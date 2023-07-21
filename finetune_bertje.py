"""Use the Annotation class to process the annotations and fine-tune BERTje for
event prediction
"""

import json
import sys
import warnings
from pprint import pprint
import threading
import time
import psutil
import nvidia_smi
import evaluate
from numpy import argmax
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    DataCollatorForTokenClassification,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
)
from util import Annotation

# set warning levels
warnings.simplefilter('ignore')

MODEL_NAME = 'GroNLP/bert-base-dutch-cased'
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
seqeval = evaluate.load("seqeval")
label_list = ['O', 'nonrealis', 'realis']

# code used to track resources
nvidia_smi.nvmlInit()
gpu_handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
START_TIME = time.time()
LOG_FILEPATH = './logs/resource_usage.log'
LOG_INTERVAL = 1.0


def log(message: str, comment=False) -> None:
    """Appends the log message to LOG_FILEPATH and includes the time"""

    with open(LOG_FILEPATH, 'a', encoding='UTF-8') as outp:
        if comment:
            outp.write(f'# {round(time.time() - START_TIME)}\t{message}\n')
        else:
            outp.write(f'{round(time.time() - START_TIME)}\t{message}\n')


def track_resources() -> None:
    """Uses a thread to print the resources to a file every [interval] seconds"""
    thread = threading.Timer(LOG_INTERVAL, track_resources)
    thread.daemon = True
    thread.start()

    gpu_usage = nvidia_smi.nvmlDeviceGetUtilizationRates(gpu_handle)

    log(
        f'{psutil.cpu_percent()}\t{psutil.virtual_memory().percent}\t{gpu_usage.gpu}\t{gpu_usage.memory}'
    )


def load_dataset(filepath: str) -> Dataset:
    """Converts the label studio json export to a Dataset class"""

    with open(filepath, 'r', encoding='UTF-8') as inp:
        annotations_json = json.load(inp)

    annotations = [Annotation(annotation) for annotation in annotations_json]
    dataset = Dataset.from_list(
        [
            {'id': index, **annotation.get_events_training_data()}
            for index, annotation in enumerate(annotations)
        ]
    )

    dataset = dataset.train_test_split(test_size=0.25, seed=123)

    tokenized_dataset = dataset.map(pre_process_data, batched=True)

    return tokenized_dataset


def pre_process_data(examples: dict[str, list]) -> dict[str, list]:
    """Tokenizes the tokens, and aligns the labels."""

    tokenized_inputs = tokenizer(
        examples["tokens"], truncation=True, is_split_into_words=True
    )

    labels = []
    for index, label in enumerate(examples['event_tags']):
        # Map tokens to their respective word.
        word_ids = tokenized_inputs.word_ids(batch_index=index)
        previous_word_idx = None
        label_ids = []
        # Set the special tokens to -100.
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)
            # Only label the first token of a given word.
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])

        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs


def compute_metrics(p):
    """Uses seqval to compute metrics while fine-tuning the model"""
    predictions, labels = p
    predictions = argmax(predictions, axis=2)

    # Remove ignored index (special tokens)
    true_predictions = [
        [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    results = seqeval.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "f1": results["overall_f1"],
        "accuracy": results["overall_accuracy"],
    }


def init_model() -> AutoModelForTokenClassification:
    """Function used to initialize model. Using this in combination with
    TrainingArguments seed ensures reproducibility across runs."""

    id2label = {
        0: 'O',
        1: 'nonrealis',
        2: 'realis',
    }
    label2id = {value: key for key, value in id2label.items()}

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME, num_labels=3, id2label=id2label, label2id=label2id
    )

    return model


def fine_tune_model(dataset: Dataset, save_filepath: str) -> Trainer:
    """Fine-tunes the model using the dataset, and saves the model to the path"""

    training_args = TrainingArguments(
        output_dir='models/intermediate',
        overwrite_output_dir=True,
        seed=123,
        # learning_rate=0.00005,
        # per_device_train_batch_size=16,
        # per_device_eval_batch_size=16,
        # num_train_epochs=4,
        # weight_decay=0.01,
        no_cuda=False,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model_init=init_model,
        # model=model,
        args=training_args,
        train_dataset=dataset['train'],
        eval_dataset=dataset['test'],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(output_dir=save_filepath)

    return trainer


def evaluate_model(
    trainer: Trainer, dataset: Dataset, print_results=True
) -> dict[str, {str, int}]:
    """Uses the test set of the dataset to evaluate the model"""

    predictions, labels, _ = trainer.predict(dataset['test'])
    predictions = argmax(predictions, axis=2)

    # Remove ignored index (special tokens)
    true_predictions = [
        [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    results = seqeval.compute(predictions=true_predictions, references=true_labels)

    if print_results:
        print('\nThese are the results of the test set per event type:')
        pprint(results)

    return results


def main(argv: list[str]):
    """Loads the annotations, fine-tunes the model, and saved the new model.
    $ python3 finetune_bertje.py annotations.json models/finetuned_bertje/
    add --log as a third argument to write resource logs to a file
    """

    if len(argv) < 3:
        print('give an input- and output filename as arguments and try again')
        return

    if len(argv) == 4 and argv[3].strip() == '--log':
        # reset file
        with open(LOG_FILEPATH, 'w', encoding='UTF-8') as outp:
            outp.write('time\tCPU\tMEM\tGPU\tGPU MEM\n')
        track_resources()

        log('[load dataset]', comment=True)
        dataset = load_dataset(argv[1])

        log('[train]', comment=True)
        trainer = fine_tune_model(dataset, argv[2])

        log('[predict & evaluate]', comment=True)
        evaluation_result = evaluate_model(trainer, dataset)

    else:
        dataset = load_dataset(argv[1])
        trainer = fine_tune_model(dataset, argv[2])
        evaluation_result = evaluate_model(trainer, dataset)


if __name__ == '__main__':
    main(sys.argv)

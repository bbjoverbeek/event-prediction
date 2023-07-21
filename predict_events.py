"""Uses a fine-tuned BERTje model to predict events in texts"""
import sys
import pickle
import warnings
import os
from tqdm import tqdm
from transformers import pipeline

warnings.filterwarnings('ignore')  # ignore the dataset warning


def predict_novel_events(
    pipe: pipeline, novel_filepath: str, verbose=False
) -> list[list[dict]]:
    """Uses the model in pipeline to predict events in the novel.
    Creates a list that has a list per sentence containing a dict per event
    """

    predictions = []

    with open(novel_filepath, 'r', encoding='UTF-8') as inp:
        novel_lines = inp.readlines()

    for sentence in tqdm(novel_lines, desc='sentences', leave=False):
        predictions.append(pipe(sentence.rstrip('\n')))
        if verbose:
            tqdm.write(f'{sentence}{predictions[-1]}\n')

    return predictions


def main(argv: list[str]) -> None:
    """Takes DBNL literary texts as input and uses model to predict events
    python3 predict_events.py model/ file_with_names_of_novels.txt
    """

    NOVEL_DIRECTORY = './data/novels/'
    OVERRIDE = (
        False  # set to true to override predictions for novels that have predictions
    )

    if len(argv) < 3:
        print('provide a model and file containing filenames to predict')
        return

    # initialize model
    pipe = pipeline('token-classification', argv[1], device=0)

    # get filenames of novels to predict
    with open(argv[2], 'r', encoding='UTF-8') as inp:
        filenames = [filename.rstrip() + '.tok' for filename in inp.readlines()]

    # filter out filenames that have a prediction already
    if not OVERRIDE:
        filenames = [
            filename
            for filename in filenames
            if not os.path.exists(
                NOVEL_DIRECTORY + filename.split('.')[0] + '.predictions.pickle'
            )
        ]

    # predict events in novels and write predictions to pickle files
    progress = tqdm(filenames, desc='novels')
    for filename in progress:
        progress.set_postfix_str(filename)
        novel_predictions = predict_novel_events(
            pipe, NOVEL_DIRECTORY + filename, verbose=False
        )
        predictions_filename = (
            NOVEL_DIRECTORY + filename.split('.')[0] + '.predictions.pickle'
        )
        with open(predictions_filename, 'wb') as outp:
            pickle.dump(novel_predictions, outp, pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    main(sys.argv)

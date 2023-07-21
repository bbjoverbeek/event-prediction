"""Creates annotation tasks for events in the label studio json format"""
import os
import sys
import json
import random
from xml.etree import ElementTree
import pandas as pd
from .util import Index

from pprint import pprint


# def split_clauses(sentid, novel_name):
#     """Uses grammatical rules to split clauses into multiple lines"""

#     parse_tree = ElementTree.parse(
#         f'./openboek-main/parses/{novel_name}/{sentid}.xml')

#     root = parse_tree.getroot()

#     # Find the main clause by looking for the main verb
#     main_verb = None
#     for node in parse_tree.iter():
#         if node.attrib.get('pos', '') == 'verb' and node.attrib.get('wvorm', '') == 'pv':
#             main_verb = node
#             break

#     # Return sentence if sentence has no verb
#     if not main_verb == None:
#         print(sentid, main_verb)
#         return root.find('sentence').text

#     # Identify the subject of the main clause
#     main_subject = None
#     for child in main_verb.iter_children():
#         if child.get('rel') == 'su':
#             main_subject = child
#             break

#     # Identify the dependent clauses
#     dependent_clauses = []
#     for node in parse_tree.iter():
#         if node.get('rel') == 'body' and node.get('cat') == 'smain':
#             # This is a subordinate clause, so add it to the list
#             subject = None
#             verb = None
#             for child in node.iter_children():
#                 if child.get('rel') == 'su':
#                     subject = child
#                 elif child.pos == 'verb' and child.get('type') == 'pv':
#                     verb = child
#             if subject is not None and verb is not None:
#                 dependent_clauses.append({'subject': subject, 'verb': verb})

#     # Determine the text of each clause
#     clauses = []
#     if main_verb is not None:
#         main_clause_text = main_subject.text + ' ' + main_verb.text + ' '
#         for child in main_verb.iter_children():
#             if child != main_subject:
#                 main_clause_text += child.text + ' '
#         clauses.append(main_clause_text)
#     for clause in dependent_clauses:
#         dependent_clause_text = clause['subject'].text + \
#             ' ' + clause['verb'].text + ' '
#         for child in clause['verb'].iter_children():
#             if child != clause['subject']:
#                 dependent_clause_text += child.text + ' '
#         clauses.append(dependent_clause_text)

#     return '\n'.join(clauses)


def get_context(novel_text, sentno):
    """Returns novel[sentno], except if this is out of range.
    Then [no context] is returned

    novel_text: list[str]
    sentno: int

    return -> str
    """
    if sentno < 0:
        return "[no context]"
    if sentno >= len(novel_text):
        return "[no context]"
    # base case, strip sentence of start identifier
    return novel_text[sentno].split('|', 1)[1].rstrip()


def novel_sents_to_tasks(novel_name, novel_text):
    """Creates a task for each sentence in novel in the json format required
    for label studio.

    novel_name: str
    novel_text: list[str]

    return -> tasks in label-studio json format
    """
    novel_tasks = []
    for sentno, sentence in enumerate(novel_text):
        author, title = novel_name.split('_', 1)
        sentid, text = sentence.rstrip().split('|', 1)
        data = {
            # 'index': sentno,
            'sentid': sentid,
            'author': author,
            'title': title,
            'randomid': None,
            'text_len': text.count(' ') + 1,
            'pre_context2': get_context(novel_text, sentno - 2),
            'pre_context1': get_context(novel_text, sentno - 1),
            'text': sentence.split('|')[1],
            'post_context1': get_context(novel_text, sentno + 1),
            'post_context2': get_context(novel_text, sentno + 2)
        }
        novel_tasks.append({'data': data, 'predictions': [{'result': []}]})
    return novel_tasks


def create_novel_events_tasks(novel_name):
    """Creates the tasks for one novel"""
    with open(f'./openboek-main/tokenized/{novel_name}.tok',
              'r', encoding='utf-8') as inp:
        novel_text = inp.readlines()

    novel_tasks = novel_sents_to_tasks(novel_name, novel_text)
    return novel_tasks


def create_novel_events_predictions(novel_tasks, novel_name):
    """Pre-annotates the mentions in the label-studio tasks for a novel

    novel_tasks: tasks in label-studio json format
    novel_name: str -- used to find mentions file

    return -> tasks in label-studio json format -- now with pre-annotations
    """
    fname = f'./openboek-main/entities/{novel_name}.mentions.tsv'
    mentions = pd.read_csv(fname, sep='\t', index_col=0, quoting=3)
    index = Index(f'./openboek-main/tokenized/{novel_name}.tok')

    # add all entities to the 'predictions' of the sentence"""
    # use extracted mentions to add entity spans (predictions) to final json
    for mention_idx, mention in mentions.to_dict('index').items():
        # get character index relative to this sentence
        sent_start_idx = index.gsenttok2charidx[mention['sentno'], 0][0]
        start_idx = (index.gsenttok2charidx[
            mention['sentno'], mention['begin']][0] - sent_start_idx)
        end_idx = (index.gsenttok2charidx[
            mention['sentno'], mention['end'] - 1][1] - sent_start_idx)
        result_item = {
            'value': {
                'start': start_idx,
                'end': end_idx,
                'text': mention['text'],
                'labels': ['mention'],
            },
            'id': (novel_tasks[0]['data']['title']
                   + '_mention_id_' + str(mention_idx)),
            'from_name': 'entities',
            'to_name': 'text',
            'type': 'labels',
            'readonly': False
        }

        # append item to index in json that corresponds with 'sentno' field
        novel_tasks[mention['sentno']]['predictions'][0]['result'].append(
            result_item)

        # set id field
        novel_tasks[mention['sentno']]['predictions'][0]['id'] = \
            f'{novel_name}_{mention["sentno"]}'

    return novel_tasks


def add_random_ids(all_tasks):
    """Add unique random id fields to be able to randomize annotating"""

    # generate list of unique random ids
    random_ids = list(range(0, len(all_tasks)))
    random.shuffle(random_ids)

    for index, task in enumerate(all_tasks):
        task['data']['randomid'] = random_ids[index]
        if index == 11:
            pprint(task)

    return all_tasks


def create_annotations_with_prediction_id(all_tasks, task_amount):
    """Creates task_amount of tasks with prediction id field set.

    This is a (hopefully temporary) fix to the bug in Label Studio where
    creating a new annotation does not copy the mention spans.
    """

    for task in all_tasks:

        if not task['predictions'][0]['result']:
            # continue if there are no predictions
            continue

        task['annotations'] = []
        for _ in range(task_amount):
            task['annotations'].append(
                {'parent_prediction': task['predictions'][0]['id'],
                 'result': []}
            )

    return all_tasks


def create_events_tasks():
    """Creates the json format pre-annotated tasks for events annotation

    Do not change this function name, this function gets called by setup.py

    return -> tasks in label studio json format
    """
    if not os.path.exists('./openboek-main/'):
        print('Cannot create tasks because ./openboek-main cannot be found',
              file=sys.stderr)
        return []

    # get novel names to add to tasks
    novels = [file[:-4] for file in os.listdir('./openboek-main/original')]

    all_tasks = []

    for novel in novels:
        novel_tasks = create_novel_events_tasks(novel)
        novel_tasks = create_novel_events_predictions(novel_tasks, novel)
        all_tasks = all_tasks + novel_tasks

    # all_tasks = create_annotations_with_prediction_id(all_tasks, 3)
    all_tasks = add_random_ids(all_tasks)

    return all_tasks


def main(argv):
    """Creates the event annotation tasks for label studio.

    If no novel is provided, tasks for the whole corpus will be created. If a
    novel is provided, only tasks for that novel will be created.

    The novel has to be provided by adding any file of this novel in the
    openboek-main folder. For exaple:

    python3 events.py [../output.json] [../openboek/original/novel.txt]
    """

    # check for correct amount of command-line arguments
    if len(argv) < 2:
        print('Provide an output filename', file=sys.stderr)
        sys.exit(1)

    # prevent overwriting source files when messing up command line args
    if not argv[1].endswith('.json'):
        print('Output file is not a .json file', file=sys.stderr)
        sys.exit(1)

    # if novel is specified, only make tasks for that novel
    if len(argv) == 3:
        # do not use this function on a Windows system!
        novel_name = os.path.basename(argv[2]).split('.')[0]

        tasks = create_novel_events_tasks(novel_name)
        tasks = create_novel_events_predictions(tasks, novel_name)
        tasks = add_random_ids(tasks)
    # otherwise make tasks for all novels
    else:
        tasks = create_events_tasks()

    # write tasks as json to the output file
    with open(argv[1], 'w', encoding='utf=8') as outp:
        json.dump(tasks, outp, indent=4)


if __name__ == '__main__':
    main(sys.argv)

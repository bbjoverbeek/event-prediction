"""This file contains the code that can be used for other programs"""

import re
from pprint import pformat
from enum import Enum


class EventType(Enum):
    """The type of an event."""

    NONREALIS = 1
    REALIS = 2

    @staticmethod
    def from_str(event_type: str) -> 'EventType':
        """Concerts a string to an event type with regex"""
        if re.match(r'^(?!non)\brealis', event_type, re.IGNORECASE):
            return EventType.REALIS
        if re.match(r'(?:non).?realis', event_type, re.IGNORECASE):
            return EventType.NONREALIS
        if re.match(r'(?:ir).?realis', event_type, re.IGNORECASE):
            return EventType.NONREALIS

        raise ValueError('Could not convert the string to EventType enum')


class MentionType(Enum):
    """The type of an mention."""

    PATIENT = 3
    AGENT = 4

    @staticmethod
    def from_str(mention_type: str) -> 'MentionType':
        """Concerts a string to an event type with regex"""
        if re.match(r'agent', mention_type, re.IGNORECASE):
            return MentionType.AGENT
        if re.match(r'patient', mention_type, re.IGNORECASE):
            return MentionType.PATIENT

        raise ValueError('Could not convert the string to MentionType enum')


class Annotation:
    """This contains all the information of an annotation for a sentence
    It can also export different information for different purposes.
    """

    def __init__(self, annotation_json):
        """Sets all the annotation fields from the annotation json"""
        self.full_json = annotation_json

        # set annotation metadata
        metadata = annotation_json['data']
        self.author = metadata['author']
        self.title = metadata['title']
        self.sent_id = metadata['sentid']
        self.text = metadata['text']
        # could also add context here
        self.time_to_annotate = annotation_json['annotations'][0]['lead_time']

        # set annotation data
        self.events, self.mentions = self.process_annotations(
            annotation_json['annotations'][0]['result']
        )

    def __str__(self) -> str:
        """Returns a formatted string of the annotation json"""

        return f'{self.text}{pformat(self.events | self.mentions)}'

    def process_annotations(self, annotations) -> tuple[dict, dict]:
        """Formats the results of the annotation json into dicts with only
        the required information
        """

        events = dict()
        mentions = dict()

        all_mentions = {
            annotation['id']: annotation
            for annotation in annotations
            if annotation.get('from_name', '') == 'entities'
        }

        # ignore events that are actually mentions
        for event in [
            ann
            for ann in annotations
            if ann.get('from_name', '') == 'event' and 'mention' not in ann['id']
        ]:
            # print(annotation['value']['text'])
            event_tok_idx = self.char_tok_idx(
                event['value']['start'], event['value']['end'], self.text
            )
            events[event_tok_idx] = {
                'type': EventType.from_str(event['value']['labels'][0]),
                'separate_verb_particle': False,
                'text': event['value']['text'],
            }
            for annotation in annotations:
                # check for related sep verb particle
                if (
                    annotation.get('from_name', '') == 'sep_verb_particle'
                    and annotation['id'] == event['id']
                ):
                    events[event_tok_idx]['separate_verb_particle'] = True

                # check for related agents (annotation is a relation, going from agent to event)
                if annotation.get('to_id', '') == event['id']:
                    mention_tok_idx = self.char_tok_idx(
                        all_mentions[annotation['from_id']]['value']['start'],
                        all_mentions[annotation['from_id']]['value']['end'],
                        self.text,
                    )

                    mentions[mention_tok_idx] = mentions.get(
                        mention_tok_idx,
                        {
                            'type': MentionType.AGENT,
                            'to_event': set(),
                            'text': all_mentions[annotation['from_id']]['value'][
                                'text'
                            ],
                        },
                    )
                    mentions[mention_tok_idx]['to_event'].add(event_tok_idx)

                # check for related patients (annotation is a relation, going from event to patient)
                if annotation.get('from_id', '') == event['id']:
                    # print(annotation1, annotation['id'])
                    mention_tok_idx = self.char_tok_idx(
                        all_mentions[annotation['to_id']]['value']['start'],
                        all_mentions[annotation['to_id']]['value']['end'],
                        self.text,
                    )
                    mentions[mention_tok_idx] = mentions.get(
                        mention_tok_idx,
                        {
                            'type': MentionType.PATIENT,
                            'to_event': set(),
                            'text': all_mentions[annotation['to_id']]['value']['text'],
                        },
                    )
                    mentions[mention_tok_idx]['to_event'].add(event_tok_idx)

        return events, mentions

    def char_tok_idx(
        self, start_char_idx: int, end_char_idx: int, text: str
    ) -> tuple[int]:
        """Changes character based index into token based index"""
        # replace characters that are not selected
        text = text.replace('-', ' ').replace("'", ' ')

        text_list = [token + ' ' for token in text.split(' ')]

        start_idx = None
        char_count = 0
        for idx, token in enumerate(text_list):
            if (  # it is just one token
                char_count == start_char_idx
                and char_count + len(token.rstrip()) == end_char_idx
            ):
                return tuple([idx])

            if char_count == start_char_idx:  # the start of a multi-token sequence
                start_idx = idx

            if start_idx is not None:  # check for the end of a multi-token sequence
                if char_count + len(token.rstrip()) == end_char_idx:
                    return tuple(range(start_idx, idx + 1))

            char_count += len(token)

        raise IndexError(
            'Could not line up the start/end char index with index of a token in text'
            f'\ntext: {text}, start_idx: {start_char_idx} - end_idx: {end_char_idx} selection: {text[start_char_idx:end_char_idx+1]}'
        )

    def get_annotations_set(
        self,
        only_mentions: bool = False,
        only_events: bool = False,
        no_sep_particle: bool = False,
    ) -> set[dict]:
        """Returns the annotation in a format that allows easy inter annotator calculation"""

        annotations = set()

        # add events if they should be added, checking if sep part should be too
        if not only_mentions:
            for index, event in self.events.items():
                if no_sep_particle:
                    annotations.add((index, event['type']))
                else:
                    annotations.add(
                        (index, event['type'], event['separate_verb_particle'])
                    )

        # add mentions if they should be, add a separate mention for every event
        if not only_events:
            for index, mention in self.mentions.items():
                for event in mention['to_event']:
                    annotations.add((index, mention['type'], event))

        return annotations

    def get_events_training_data(self) -> dict[list[int | str]]:
        """Returns all the information required for training a model on events
        Does not include separate verb particles
        """

        tokens = self.text.split(' ')

        labels = []
        for token_idx, _ in enumerate(tokens):
            labels.append(0)
            for event_idx, event in self.events.items():
                if token_idx in event_idx:
                    labels[token_idx] = event['type'].value

        return {'event_tags': labels, 'tokens': tokens}


def main(argv: list[str]) -> None:
    """Main function for debugging Currently prints all annotations from a file"""

    if len(argv) != 2:
        print('Attach one file to print the annotations from.', file=sys.stderr)
        return

    with open(argv[1], 'r', encoding='UTF-8') as inp:
        annotations_json = json.load(inp)

    annotations = [Annotation(annotation) for annotation in annotations_json]

    for annotation in annotations:
        print(annotation, end='\n\n')


if __name__ == '__main__':
    import sys
    import json

    main(sys.argv)

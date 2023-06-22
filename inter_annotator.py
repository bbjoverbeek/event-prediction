"""Uses the Annotation class to compute inter annotator agreement"""
import argparse
import json
from io import TextIOWrapper
from statistics import fmean
from itertools import combinations
from util import Annotation


def parse_args() -> argparse.Namespace:
    """Creates an argument parser for the program"""
    parser = argparse.ArgumentParser(
        prog='Inter Annotator Agreement program',
        description='Computes the inter annotator agreement for Openboek event annotations',
    )

    # add arguments for annotation files
    parser.add_argument(
        'annotation_filepaths',
        type=argparse.FileType('r', encoding='UTF-8'),
        help='Label Studio .json export of the annotations per annotator',
        nargs='+',
    )

    # allow only computing agreement for events or only mentions
    group1 = parser.add_mutually_exclusive_group(required=False)
    group1.add_argument(
        '--only-events',
        action='store_true',
        help='only compute inter annotator for events',
    )

    mentions = group1.add_argument(
        '--only-mentions',
        action='store_true',
        help='only compute inter annotator for agent/patient',
    )

    # allow not taking sep verb particle into account
    group2 = parser.add_mutually_exclusive_group(required=False)
    group2.add_argument(
        '--no-sep-particle',
        action='store_true',
        help='ignore the separate verb particle',
    )
    group2._group_actions.append(mentions)

    args = parser.parse_args()

    # error if not enough files are provided
    if len(args.annotation_filepaths) < 2:
        parser.error(
            'Provide at least two annotation files to compute inter annotator agreement.'
        )

    # error if the files are not json files
    for filepath in args.annotation_filepaths:
        if not filepath.name.endswith('.json'):
            parser.error('The annotation files should be .json format')

    return args


def load_annotations(files: list[TextIOWrapper]) -> list[list[Annotation]]:
    """Loads all the annotations and checks if they are equal in length"""
    all_annotations = []
    for file in files:
        annotations_json = json.load(file)
        file.close()

        all_annotations.append(
            [Annotation(annotation) for annotation in annotations_json]
        )

    # check if all of them are equal in length
    annotation_lengths = [len(annotations) for annotations in all_annotations]
    if not all(annotation_lengths):
        raise IndexError(
            f'Not all files have the same number of annotations: {annotation_lengths}'
        )

    return all_annotations


def compute_inter_annotator(
    annotations: list[list[Annotation]],
    only_mentions: bool = False,
    only_events: bool = False,
    no_sep_particle: bool = False,
) -> dict[str, dict[str, float]]:
    """Compute the inter annotator agreement of all annotations.
    Can also only compute for specific annotations."""

    precision, recall, f1 = [], [], []

    for combi in combinations(annotations, 2):
        tp, fp, fn = 0, 0, 0
        for annotations1, annotations2 in zip(combi[0], combi[1]):
            annotations1_set = annotations1.get_annotations_set(
                only_mentions=only_mentions,
                only_events=only_events,
                no_sep_particle=no_sep_particle,
            )
            annotations2_set = annotations2.get_annotations_set(
                only_mentions=only_mentions,
                only_events=only_events,
                no_sep_particle=no_sep_particle,
            )

            tp += len(annotations1_set & annotations2_set)
            fp += len(annotations2_set - annotations1_set)
            fn += len(annotations1_set - annotations2_set)

        precision.append(tp / (tp + fp) if tp + fp > 0 else 0)
        recall.append(tp / (tp + fn) if tp + fn > 0 else 0)
        f1.append(
            (2 * precision[-1] * recall[-1]) / (precision[-1] + recall[-1])
            if precision[-1] + recall[-1] > 0
            else 0
        )

    return {
        'precision': fmean(precision),
        'recall': fmean(recall),
        'f1-score': fmean(f1),
    }


def main():
    """Computes an inter annotator score based on the command line input"""

    args = parse_args()

    annotations = load_annotations(args.annotation_filepaths)

    scores = compute_inter_annotator(
        annotations,
        only_mentions=args.only_mentions,
        only_events=args.only_events,
        no_sep_particle=args.no_sep_particle,
    )

    print('\nThese are the final scores (averages if num annotators > 2):')
    print(
        f'f1-score: {scores["f1-score"]:.3f} | precision: {scores["precision"]:.3f} | recall: {scores["recall"]:.3f}\n'
    )


if __name__ == '__main__':
    main()

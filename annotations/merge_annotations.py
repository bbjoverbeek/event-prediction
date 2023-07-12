"""Script to merge separate Label Studio annotation file into one"""
import sys
import json
import more_itertools as mit


def main(argv: list[str]):
    """Opens annotatoin files, merges them, and writes them to a new file.
    Last argument is the output file:
    python3 merge_annotations.py export1.json export2.json [add more here] merged.json
    """

    all_annotations = []

    # open all the files
    for filepath in argv[1:-1]:
        with open(filepath, 'r', encoding='UTF-8') as inp:
            annotations = json.load(inp)
            all_annotations += annotations
            print(f'{filepath} has {len(annotations)} annotations.')

    print('\nperforming checks before merging:')
    # check for double annotations
    randomids = set()
    double_found = False
    for annotation in all_annotations:
        if int(annotation['data']['randomid']) in randomids:
            print(f'{annotation["data"]["randomid"]} occurs multiple times.')
            double_found = True
        else:
            randomids.add(int(annotation['data']['randomid']))

    if not double_found:
        print('No duplicate annotations have been found')

    # checks for missing annotations
    all_randomids = set(range(min(randomids), max(randomids) + 1))

    missing_ids = [
        list(group) for group in mit.consecutive_groups(all_randomids - randomids)
    ]

    if missing_ids:
        print('The annotations with the following randomids are missing:')
        for group in missing_ids:
            if len(group) > 1:
                print(f'{group[0]}-{group[-1]}')
            else:
                print(group[0])

    else:
        print('No missing annotations were found')

    # write combined to output file
    with open(argv[-1], 'w', encoding='UTF-8') as outp:
        json.dump(all_annotations, outp)

    print(f"\nSuccessfully wrote all {len(all_annotations)} to '{argv[-1]}'")


if __name__ == '__main__':
    main(sys.argv)

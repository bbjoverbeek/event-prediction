"""Script to set up Label Studio with our projects"""
import sys
import os
import requests
from label_studio_sdk import Client
from config import API_KEY

# sets the URL to the url set in run.sh
# defaults to localhost if environment variables are not set
LABEL_STUDIO_URL = os.getenv('LABEL_STUDIO_HOST', 'http://localhost') + \
    ':' + os.getenv('LABEL_STUDIO_PORT', '8787')


def create_project(ls_client, project_name):
    """Creates an annotation project

    Also sets the interface, creates tasks if not present, and imports the tasks
    """

    print(f'Creating {project_name} project')

    # open the interface file
    try:
        with open('./interface.xml', 'r', encoding='utf-8') as inp:
            interface = inp.read()
    except FileNotFoundError as err:
        print(
            f'There is no interace file for \'{project_name}\', so the project'
            f'was not created:\n{err}\n', file=sys.stderr
        )
        return

    # create the project and set the interface
    try:
        project = ls_client.start_project(
            title=project_name,
            description=f'Openboek annotation task for {project_name}',
            label_config=interface
        )
    except requests.exceptions.HTTPError as err:
        print(
            f'The interface for \'{project_name}\' is not valid, so the project '
            f'was not created:\n{err}\n', file=sys.stderr
        )
        return

    # import the annotation tasks
    try:
        project.import_tasks('./pre-annotations.json')
    except requests.exceptions.HTTPError as err:
        print(
            f'Something went wrong trying to import the annotation tasks for '
            f'\'{project_name}\':\n{err}\nTry checking the contents of the '
            f'./pre_annotations/{project_name}.json file.\n', file=sys.stderr
        )
        return

    print(f'Successfully created the {project_name} project!\n')

    return


def main():
    """Links Label Studio SDK and creates different projects

    Has to be run if label-studio server is running.
    """
    # initialize Label Studio Client
    try:
        ls_client = Client(url=LABEL_STUDIO_URL, api_key=API_KEY)
    except AttributeError as err:
        print(f'Do not forget to enter the API key in config.py\n{err}',
              file=sys.stderr)

    # see if connection is properly initialized
    try:
        ls_client.check_connection()
        print('Connected to label studio instance!')
    except requests.exceptions.ConnectionError as err:
        print(f'Could not connect to Label Studio, is it running?\n{err}')
        sys.exit(1)

    create_project(ls_client, 'events')

    print(f'The created projects are now visible at {LABEL_STUDIO_URL}')


if __name__ == "__main__":
    main()

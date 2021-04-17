import os.path

DELETE_MARKER_MESSAGE = '''\
This file is placed here by pip to indicate the source was put
here by pip.

Once this package is successfully installed this source code will be
deleted (unless you remove this file).
'''
PIP_DELETE_MARKER_FILENAME = 'pip-delete-this-directory.txt'


def write_delete_marker_file(directory):
    # type: (str) -> None
    """
    Write the pip delete marker file into this directory.
    """
    filepath = os.path.join(directory, PIP_DELETE_MARKER_FILENAME)
    with open(filepath, 'w') as marker_fp:
        marker_fp.write(DELETE_MARKER_MESSAGE)

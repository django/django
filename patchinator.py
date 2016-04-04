#!/usr/bin/python
"""
Script that automatically generates a Django patch from the Channels codebase
based on some simple rules and string replacements.

Once Channels lands in Django, will be reversed to instead generate this
third-party app from the now-canonical Django source.
"""

import re
import os.path
import sys


# Transforms: Turn one content string into another

class Replacement(object):
    """
    Represents a string replacement in a file; uses a regular expression to
    substitute strings in the file.
    """

    def __init__(self, match, sub):
        self.match = match
        self.sub = sub

    def __call__(self, value):
        return re.sub(self.match, self.sub, value)


class Insert(object):
    """
    Inserts a string before/after another in a file, one time only, with multiline match.
    """

    def __init__(self, match, to_insert, after=False):
        self.match = match
        self.to_insert = to_insert
        self.after = after

    def __call__(self, value):
        match = re.search(self.match, value, flags=re.MULTILINE)
        if not match:
            raise ValueError("Could not find match %s" % self.match)
        if self.after:
            return value[:match.end()] + self.to_insert + value[match.end():]
        else:
            return value[:match.start()] + self.to_insert + value[match.start():]


# Operations: Copy or patch files

class FileMap(object):
    """
    Represents a file map from the source to the destination, with
    optional extra regex transforms.
    """

    def __init__(self, source_path, dest_path, transforms, makedirs=True):
        self.source_path = source_path
        self.dest_path = dest_path
        self.transforms = transforms
        self.makedirs = makedirs

    def run(self, source_dir, dest_dir):
        print("COPY: %s -> %s" % (self.source_path, self.dest_path))
        # Open and read in source file
        source = os.path.join(source_dir, self.source_path)
        with open(source, "r") as fh:
            content = fh.read()
        # Run transforms
        for transform in self.transforms:
            content = transform(content)
        # Save new file
        dest = os.path.join(dest_dir, self.dest_path)
        if self.makedirs:
            if not os.path.isdir(os.path.dirname(dest)):
                os.makedirs(os.path.dirname(dest))
        with open(dest, "w") as fh:
            fh.write(content)


class NewFile(object):
    """
    Writes a file to the destination, either blank or with some content from
    a string.
    """

    def __init__(self, dest_path, content=""):
        self.dest_path = dest_path
        self.content = content

    def run(self, source_dir, dest_dir):
        print("NEW: %s" % (self.dest_path, ))
        # Save new file
        dest = os.path.join(dest_dir, self.dest_path)
        with open(dest, "w") as fh:
            fh.write(self.content)


# Main class and config


global_transforms = [
    Replacement(r"import channels.([a-zA-Z0-9_\.]+)$", r"import django.channels.\1 as channels"),
    Replacement(r"from channels import", r"from django.channels import"),
    Replacement(r"from channels.([a-zA-Z0-9_\.]+) import", r"from django.channels.\1 import"),
    Replacement(r"from .handler import", r"from django.core.handlers.asgi import")
]

docs_transforms = global_transforms + [
    Replacement(r":doc:`concepts`", r":doc:`topics/channels/concepts`"),
    Replacement(r":doc:`deploying`", r":doc:`topics/channels/deploying`"),
    Replacement(r":doc:`scaling`", r":doc:`topics/channels/scaling`"),
    Replacement(r":doc:`getting-started`", r":doc:`intro/channels`"),
    Replacement(r"\n\(.*installation>`\)\n", r""),
]


class Patchinator(object):

    operations = [
        FileMap(
            "channels/asgi.py", "django/channels/asgi.py", global_transforms,
        ),
        FileMap(
            "channels/auth.py", "django/channels/auth.py", global_transforms,
        ),
        FileMap(
            "channels/channel.py", "django/channels/channel.py", global_transforms,
        ),
        FileMap(
            "channels/database_layer.py", "django/channels/database_layer.py", global_transforms,
        ),
        FileMap(
            "channels/exceptions.py", "django/channels/exceptions.py", global_transforms,
        ),
        FileMap(
            "channels/handler.py", "django/core/handlers/asgi.py", global_transforms,
        ),
        FileMap(
            "channels/routing.py", "django/channels/routing.py", global_transforms,
        ),
        FileMap(
            "channels/sessions.py", "django/channels/sessions.py", global_transforms,
        ),
        FileMap(
            "channels/staticfiles.py", "django/channels/staticfiles.py", global_transforms,
        ),
        FileMap(
            "channels/utils.py", "django/channels/utils.py", global_transforms,
        ),
        FileMap(
            "channels/worker.py", "django/channels/worker.py", global_transforms,
        ),
        FileMap(
            "channels/management/commands/runworker.py",
            "django/core/management/commands/runworker.py",
            global_transforms,
        ),
        # Tests
        FileMap(
            "channels/tests/base.py", "django/test/channels.py", global_transforms,
        ),
        NewFile(
            "tests/channels_tests/__init__.py",
        ),
        FileMap(
            "channels/tests/test_database_layer.py", "tests/channels_tests/test_database_layer.py", global_transforms,
        ),
        FileMap(
            "channels/tests/test_handler.py", "tests/channels_tests/test_handler.py", global_transforms,
        ),
        FileMap(
            "channels/tests/test_routing.py", "tests/channels_tests/test_routing.py", global_transforms,
        ),
        FileMap(
            "channels/tests/test_request.py", "tests/channels_tests/test_request.py", global_transforms,
        ),
        # Docs
        FileMap(
            "docs/backends.rst", "docs/ref/channels/backends.txt", docs_transforms,
        ),
        FileMap(
            "docs/concepts.rst", "docs/topics/channels/concepts.txt", docs_transforms,
        ),
        FileMap(
            "docs/deploying.rst", "docs/topics/channels/deploying.txt", docs_transforms,
        ),
        FileMap(
            "docs/getting-started.rst", "docs/intro/channels.txt", docs_transforms,
        ),
        FileMap(
            "docs/reference.rst", "docs/ref/channels/api.txt", docs_transforms,
        ),
        FileMap(
            "docs/scaling.rst", "docs/topics/channels/scaling.txt", docs_transforms,
        ),
    ]

    def __init__(self, source, destination):
        self.source = os.path.abspath(source)
        self.destination = os.path.abspath(destination)

    def run(self):
        print("Patchinator running.\n Source: %s\n Destination: %s" % (self.source, self.destination))
        for operation in self.operations:
            operation.run(self.source, self.destination)


if __name__ == '__main__':
    try:
        Patchinator(os.path.dirname(__file__), sys.argv[1]).run()
    except IndexError:
        print("Supply the target Django directory on the command line")

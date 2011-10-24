import os

from django.core.management.base import copy_helper, CommandError, LabelCommand
from django.utils.importlib import import_module

class Command(LabelCommand):
    help = "Creates a Django app directory structure for the given app name in the current directory."
    args = "[appname]"
    label = 'application name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    def handle_label(self, app_name, directory=None, **options):
        if directory is None:
            directory = os.getcwd()

        # Check that the app_name cannot be imported.
        try:
            import_module(app_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing Python module and cannot be used as an app name. Please try another name." % app_name)

        copy_helper(self.style, 'app', app_name, directory)

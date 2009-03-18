from django.core.management.base import copy_helper, CommandError, LabelCommand
from django.utils.importlib import import_module
import os
import re
from random import choice

class Command(LabelCommand):
    help = "Creates a Django project directory structure for the given project name in the current directory."
    args = "[projectname]"
    label = 'project name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    def handle_label(self, project_name, **options):
        # Determine the project_name a bit naively -- by looking at the name of
        # the parent directory.
        directory = os.getcwd()

        # Check that the project_name cannot be imported.
        try:
            import_module(project_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing Python module and cannot be used as a project name. Please try another name." % project_name)

        copy_helper(self.style, 'project', project_name, directory)

        # Create a random SECRET_KEY hash, and put it in the main settings.
        main_settings_file = os.path.join(directory, project_name, 'settings.py')
        settings_contents = open(main_settings_file, 'r').read()
        fp = open(main_settings_file, 'w')
        secret_key = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
        settings_contents = re.sub(r"(?<=SECRET_KEY = ')'", secret_key + "'", settings_contents)
        fp.write(settings_contents)
        fp.close()

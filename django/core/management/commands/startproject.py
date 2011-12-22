from random import choice

from django.core.management.base import CommandError
from django.core.management.templates import TemplateCommand
from django.utils.importlib import import_module


class Command(TemplateCommand):
    help = ("Creates a Django project directory structure for the given "
            "project name in the current directory or optionally in the "
            "given directory.")

    def handle(self, project_name=None, target=None, *args, **options):
        if project_name is None:
            raise CommandError("you must provide a project name")

        # Check that the project_name cannot be imported.
        try:
            import_module(project_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing "
                               "Python module and cannot be used as a "
                               "project name. Please try another name." %
                               project_name)

        # Create a random SECRET_KEY hash to put it in the main settings.
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        options['secret_key'] = ''.join([choice(chars) for i in range(50)])

        super(Command, self).handle('project', project_name, target, **options)

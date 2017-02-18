from importlib import import_module

from django.core.management.base import CommandError
from django.core.management.templates import TemplateCommand


class Command(TemplateCommand):
    help = ("Creates a Django app directory structure for the given app "
            "name in the current directory or optionally in the given "
            "directory.")
    missing_args_message = "You must provide an application name."

    def handle(self, **options):
        app_name, target = options.pop('name'), options.pop('directory')
        self.validate_name(app_name, "app")

        # Check that the app_name cannot be imported.
        try:
            import_module(app_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing "
                               "Python module and cannot be used as an app "
                               "name. Please try another name." % app_name)

        super(Command, self).handle('app', app_name, target, **options)

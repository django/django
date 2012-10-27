from django.core.management.base import CommandError
from django.core.management.templates import TemplateCommand
from django.utils.importlib import import_module


class Command(TemplateCommand):
    help = ("Creates a Django app directory structure for the given app "
            "name in the current directory or optionally in the given "
            "directory.")

    def handle(self, app_name=None, target=None, **options):
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

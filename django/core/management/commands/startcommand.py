from django.core.management.templates import TemplateCommand
import os


class Command(TemplateCommand):
    help = (
        "Creates a Django management command for the given command name  "
        "in the management/commands folder of the specified app."
    )

    missing_args_message = "You must provide an application and command name"

    def handle(self, **options):
        app_name = options.pop('name')
        command_name = options.pop('command')

        target = os.path.abspath(os.path.join(os.getcwd(), app_name, "management", "commands"))

        super().handle('command', command_name, target, **options)

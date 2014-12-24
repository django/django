from importlib import import_module
from locale import getlocale, getdefaultlocale

from django.core.management.base import CommandError
from django.core.management.templates import TemplateCommand
from django.utils.crypto import get_random_string


class Command(TemplateCommand):
    help = ("Creates a Django project directory structure for the given "
            "project name in the current directory or optionally in the "
            "given directory.")
    missing_args_message = "You must provide a project name."

    def handle(self, **options):
        project_name, target = options.pop('name'), options.pop('directory')
        self.validate_name(project_name, "project")

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

        # Create a random SECRET_KEY to put it in the main settings.
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        options['secret_key'] = get_random_string(50, chars)

        # Find out the language code to set in the settings.
        try:
            # get the current locale, or fall back to default locale if none is set
            locale = getlocale()[0] or getdefaultlocale()[0]

            # translate e.g. "sv_SE" to django locale format "sv-se"
            language_code = locale.lower().replace("_", "-")

            # now check if this is actually a locale django supports out of the box
            from django.conf import global_settings
            available_languages = dict(global_settings.LANGUAGES)

            # try to see if the exact variant exists translated, e.g. "pt-br" or at least "pt" exists
            if language_code in available_languages or language_code.split('-')[0] in available_languages:
                options['language_code'] = language_code
            # if the language isn't available, fall back to US english.
            else:
                options['language_code'] = 'en-us'

        except:
            # If anything whatsoever goes wrong, just fallback to default language
            options['language_code'] = 'en-us'

        super(Command, self).handle('project', project_name, target, **options)

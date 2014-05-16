import warnings

from django.core.management.base import BaseCommand
from django.utils.deprecation import RemovedInDjango19Warning


class Command(BaseCommand):
    help = "Runs this project as a FastCGI application. Requires flup."
    args = '[various KEY=val options, use `runfcgi help` for help]'

    def handle(self, *args, **options):
        warnings.warn(
            "FastCGI support has been deprecated and will be removed in Django 1.9.",
            RemovedInDjango19Warning)

        from django.conf import settings
        from django.utils import translation
        # Activate the current language, because it won't get activated later.
        try:
            translation.activate(settings.LANGUAGE_CODE)
        except AttributeError:
            pass
        from django.core.servers.fastcgi import runfastcgi
        runfastcgi(args)

    def usage(self, subcommand):
        from django.core.servers.fastcgi import FASTCGI_HELP
        return FASTCGI_HELP

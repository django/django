import warnings

from freedom.core.management.base import BaseCommand
from freedom.utils.deprecation import RemovedInFreedom19Warning


class Command(BaseCommand):
    help = "Runs this project as a FastCGI application. Requires flup."
    args = '[various KEY=val options, use `runfcgi help` for help]'

    def handle(self, *args, **options):
        warnings.warn(
            "FastCGI support has been deprecated and will be removed in Freedom 1.9.",
            RemovedInFreedom19Warning)

        from freedom.conf import settings
        from freedom.utils import translation
        # Activate the current language, because it won't get activated later.
        try:
            translation.activate(settings.LANGUAGE_CODE)
        except AttributeError:
            pass
        from freedom.core.servers.fastcgi import runfastcgi
        runfastcgi(args)

    def usage(self, subcommand):
        from freedom.core.servers.fastcgi import FASTCGI_HELP
        return FASTCGI_HELP

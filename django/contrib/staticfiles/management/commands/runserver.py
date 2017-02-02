from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.management.commands.runserver import \
    Command as RunserverCommand


class Command(RunserverCommand):
    help = "Starts a lightweight Web server for development and also serves static files."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--nostatic', action="store_false", dest='use_static_handler', default=True,
            help='Tells Django to NOT automatically serve static files at STATIC_URL.',
        )
        parser.add_argument(
            '--insecure', action="store_true", dest='insecure_serving', default=False,
            help='Allows serving static files even if DEBUG is False.',
        )

    def get_handler(self, *args, **options):
        """
        Returns the static files serving handler wrapping the default handler,
        if static files should be served. Otherwise just returns the default
        handler.
        """
        handler = super().get_handler(*args, **options)
        use_static_handler = options['use_static_handler']
        insecure_serving = options['insecure_serving']
        if use_static_handler and (settings.DEBUG or insecure_serving):
            return StaticFilesHandler(handler)
        return handler

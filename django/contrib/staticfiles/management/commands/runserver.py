from optparse import make_option

from django.conf import settings
from django.core.management.commands.runserver import BaseRunserverCommand

from django.contrib.staticfiles.handlers import StaticFilesHandler

class Command(BaseRunserverCommand):
    option_list = BaseRunserverCommand.option_list + (
        make_option('--nostatic', action="store_false", dest='use_static_handler', default=True,
            help='Tells Django to NOT automatically serve static files at STATIC_URL.'),
        make_option('--insecure', action="store_true", dest='insecure_serving', default=False,
            help='Allows serving static files even if DEBUG is False.'),
    )
    help = "Starts a lightweight Web server for development, including static files serving."

    def get_handler(self, *args, **options):
        """
        Returns the static files serving handler.
        """
        handler = super(Command, self).get_handler(*args, **options)
        use_static_handler = options.get('use_static_handler', True)
        insecure_serving = options.get('insecure_serving', False)
        if (settings.DEBUG and use_static_handler or
                (use_static_handler and insecure_serving)):
            handler = StaticFilesHandler(handler)
        return handler

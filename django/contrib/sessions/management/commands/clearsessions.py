from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils.importlib import import_module


class Command(NoArgsCommand):
    help = "Can be run as a cronjob or directly to clean out expired sessions (only with the database backend at the moment)."

    def handle_noargs(self, **options):
        engine = import_module(settings.SESSION_ENGINE)
        try:
            engine.SessionStore.clear_expired()
        except NotImplementedError:
            self.stderr.write("Session engine '%s' doesn't support clearing "
                              "expired sessions.\n" % settings.SESSION_ENGINE)

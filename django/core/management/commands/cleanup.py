from django.core.management.base import NoArgsCommand
from django.utils.importlib import import_module
from django.conf import settings

class Command(NoArgsCommand):
    help = "Can be run as a cronjob or directly to clean out old data from the database (only expired sessions at the moment)."

    def handle_noargs(self, **options):
        engine = import_module(settings.SESSION_ENGINE)
        engine.SessionStore.cleanup()

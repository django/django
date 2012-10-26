from django.core.management.base import NoArgsCommand
from django.utils.importlib import import_module
from django.conf import settings


class Command(NoArgsCommand):
    help = "Clean expired sessions."

    def handle_noargs(self, **options):
        engine = import_module(settings.SESSION_ENGINE)
        engine.SessionStore.cleanup()

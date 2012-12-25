import warnings

from django.contrib.sessions.management.commands import clearsessions


class Command(clearsessions.Command):
    def handle_noargs(self, **options):
        warnings.warn(
            "The `cleanup` command has been deprecated in favor of `clearsessions`.",
            DeprecationWarning)
        super(Command, self).handle_noargs(**options)

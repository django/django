from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = "Runs the command-line client for the current DATABASE_ENGINE."

    requires_model_validation = False

    def handle_noargs(self, **options):
        from django.db import runshell
        runshell()

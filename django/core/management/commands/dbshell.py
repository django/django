from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Runs the command-line client for the current DATABASE_ENGINE."

    requires_model_validation = False

    def handle(self, **options):
        from django.db import runshell
        runshell()

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "This command is stored as a package."

    def handle(self, *args, **options):
        self.stdout.write("I've been called from a package.")

from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key

class Command(BaseCommand):
    help = "Generate a new Django SECRET_KEY."

    def handle(self, *args, **options):
        self.stdout.write(get_random_secret_key())

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, **options):
        self.stdout.write("simple_app")

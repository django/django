from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--version', action='version', version='A.B.C')

    def handle(self, *args, **options):
        pass

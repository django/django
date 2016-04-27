from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", dest="list", help="Print all options")

    def handle(self, *args, **options):
        pass

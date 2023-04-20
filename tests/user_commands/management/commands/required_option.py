from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-n", "--need-me", required=True)
        parser.add_argument("-t", "--need-me-too", required=True, dest="needme2")

    def handle(self, *args, **options):
        self.stdout.write(",".join(options))

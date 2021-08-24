from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--set")

    def handle(self, **options):
        self.stdout.write("Set %s" % options["set"])

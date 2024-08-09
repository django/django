from django.core.management.base import BaseCommand
from django.db.migrations.autodetector import MigrationAutodetector


class MigrationCommand(BaseCommand):
    autodetector_class = MigrationAutodetector

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

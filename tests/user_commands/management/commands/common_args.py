from argparse import ArgumentError

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    def add_arguments(self, parser):
        try:
            parser.add_argument("--version", action="version", version="A.B.C")
        except ArgumentError:
            pass
        else:
            raise CommandError("--version argument does no yet exist")

    def handle(self, *args, **options):
        return "Detected that --version already exists"

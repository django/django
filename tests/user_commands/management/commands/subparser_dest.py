from django.core.management.base import BaseCommand
from django.utils.version import PY37


class Command(BaseCommand):
    def add_arguments(self, parser):
        kwargs = {'required': True} if PY37 else {}
        subparsers = parser.add_subparsers(dest='subcommand', **kwargs)
        parser_foo = subparsers.add_parser('foo')
        parser_foo.add_argument('--bar')

    def handle(self, *args, **options):
        self.stdout.write(','.join(options))

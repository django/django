from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--foo-id', type=int, nargs='?', default=None)
        group.add_argument('--foo-name', type=str, nargs='?', default=None)

    def handle(self, *args, **options):
        self.stdout.write(','.join(options))

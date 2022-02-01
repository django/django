from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--foo-list', nargs='+', type=int, required=True)

    def handle(self, *args, **options):
        for option, value in options.items():
            self.stdout.write('%s=%s' % (option, value))

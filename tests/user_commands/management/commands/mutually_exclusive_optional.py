from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        # Non-required mutually exclusive group
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--option-a', type=str, default=None, dest='option_a')
        group.add_argument('--option-b', type=str, default=None, dest='option_b')

    def handle(self, *args, **options):
        self.stdout.write(','.join(str(options.get(key)) for key in ['option_a', 'option_b']))

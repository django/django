from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test basic commands'
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--option_a', '-a', default='1')
        parser.add_argument('--option_b', '-b', default='2')
        parser.add_argument('--option_c', '-c', default='3')

    def handle(self, *labels, **options):
        print('EXECUTE:BaseCommand labels=%s, options=%s' % (labels, sorted(options.items())))

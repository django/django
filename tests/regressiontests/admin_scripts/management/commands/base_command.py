from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--option_a','-a', action='store', dest='option_a', default='1'),
        make_option('--option_b','-b', action='store', dest='option_b', default='2'),
        make_option('--option_c','-c', action='store', dest='option_c', default='3'),
    )
    help = 'Test basic commands'
    requires_model_validation = False
    args = '[labels ...]'

    def handle(self, *labels, **options):
        print('EXECUTE:BaseCommand labels=%s, options=%s' % (labels, sorted(options.items())))

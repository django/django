from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Test basic commands'
    requires_model_validation = False
    args = '[labels ...]'

    def handle(self, *labels, **options):
        print 'EXECUTE:BaseCommand labels=%s, options=%s' % (labels, sorted(options.items()))

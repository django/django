from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Test managment commands in namespaced apps'
    requires_model_validation = False
    args = ''

    def handle(self, *labels, **options):
        print 'EXECUTE:app1_command1'

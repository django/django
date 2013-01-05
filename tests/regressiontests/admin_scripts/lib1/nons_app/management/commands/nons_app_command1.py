from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Test managment commands in non-namespaced app'
    requires_model_validation = False
    args = ''

    def handle(self, *labels, **options):
        print 'EXECUTE:nons_app_command1'

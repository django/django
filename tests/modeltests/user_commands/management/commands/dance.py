from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Dance around like a madman."
    args = ''
    requires_model_validation = True

    def handle(self, *args, **options):
        print "I don't feel like dancing."
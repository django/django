from django.core.management.base import BaseCommand


class Command(BaseCommand):

    private_options = ('stdout', )

    def handle(self, **options):
        self.stdout.write('simple_app')

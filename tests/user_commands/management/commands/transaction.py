from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Say hello."
    args = ''
    output_transaction = True
    private_options = ('stdout', )

    def handle(self, *args, **options):
        return 'Hello!'

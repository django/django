from django.core.management.base import BaseCommand
from django.utils import translation


class Command(BaseCommand):

    leave_locale_alone = True
    private_options = ('stdout', )

    def handle(self, *args, **options):
        return translation.get_language()

from django.core.management.base import BaseCommand
from django.utils import translation


class Command(BaseCommand):

    can_import_settings = True
    leave_locale_alone = True

    def handle(self, *args, **options):
        return translation.get_language()

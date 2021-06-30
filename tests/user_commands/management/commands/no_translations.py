from mango.core.management.base import BaseCommand, no_translations
from mango.utils import translation


class Command(BaseCommand):

    @no_translations
    def handle(self, *args, **options):
        return translation.get_language()

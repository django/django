from freedom.core.management.base import BaseCommand
from freedom.utils import translation


class Command(BaseCommand):

    can_import_settings = True
    leave_locale_alone = False

    def handle(self, *args, **options):
        return translation.get_language()

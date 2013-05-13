from django.core.compat_checks.base import check_compatibility
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        check_compatibility()

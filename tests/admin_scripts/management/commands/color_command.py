from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test color output"
    requires_system_checks = False

    def handle(self, **options):
        return self.style.SQL_KEYWORD('BEGIN')

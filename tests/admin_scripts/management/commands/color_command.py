from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Test color output"
    requires_system_checks = False

    def handle_noargs(self, **options):
        return self.style.SQL_KEYWORD('BEGIN')

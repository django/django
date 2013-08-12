from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Validates all installed models."

    requires_system_checks = False

    def handle_noargs(self, **options):
        self.check(display_num_errors=True)

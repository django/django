from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = "Validates all installed models."

    requires_model_validation = False

    def handle_noargs(self, **options):
        self.validate(display_num_errors=True)

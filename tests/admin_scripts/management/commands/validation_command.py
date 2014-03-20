from django.core.management.base import NoArgsCommand


class InvalidCommand(NoArgsCommand):
    help = ("Test raising an error if both requires_system_checks "
            "and requires_model_validation are defined.")
    requires_system_checks = True
    requires_model_validation = True

    def handle_noargs(self, **options):
        pass

from django.core.management.base import LabelCommand


class Command(LabelCommand):
    help = "Test Label-based commands"
    requires_system_checks = []

    def handle_label(self, label, **options):
        print(f"EXECUTE:LabelCommand label={label}, options={sorted(options.items())}")

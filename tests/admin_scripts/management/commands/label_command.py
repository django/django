from django.core.management.base import LabelCommand


class Command(LabelCommand):
    help = "Test Label-based commands"
    requires_system_checks = False

    def handle_label(self, label, **options):
        print('EXECUTE:LabelCommand label=%s, options=%s' % (label, sorted(options.items())))

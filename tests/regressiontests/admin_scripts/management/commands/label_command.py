from django.core.management.base import LabelCommand


class Command(LabelCommand):
    help = "Test Label-based commands"
    requires_model_validation = False
    args = '<label>'

    def handle_label(self, label, **options):
        print 'EXECUTE:LabelCommand label=%s, options=%s' % (label, sorted(options.items()))

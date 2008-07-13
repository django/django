from django.core.management.base import LabelCommand
# Python 2.3 doesn't have sorted()
try:
    sorted
except NameError:
    from django.utils.itercompat import sorted

class Command(LabelCommand):
    help = "Test Label-based commands"
    requires_model_validation = False
    args = '<label>'

    def handle_label(self, label, **options):
        print 'EXECUTE:LabelCommand label=%s, options=%s' % (label, sorted(options.items()))

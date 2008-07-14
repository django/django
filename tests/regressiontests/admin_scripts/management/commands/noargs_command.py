from django.core.management.base import NoArgsCommand
# Python 2.3 doesn't have sorted()
try:
    sorted
except NameError:
    from django.utils.itercompat import sorted

class Command(NoArgsCommand):
    help = "Test No-args commands"
    requires_model_validation = False


    def handle_noargs(self, **options):
        print 'EXECUTE:NoArgsCommand options=%s' % sorted(options.items())

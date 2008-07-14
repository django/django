from django.core.management.base import AppCommand
# Python 2.3 doesn't have sorted()
try:
    sorted
except NameError:
    from django.utils.itercompat import sorted

class Command(AppCommand):
    help = 'Test Application-based commands'
    requires_model_validation = False
    args = '[appname ...]'

    def handle_app(self, app, **options):
        print 'EXECUTE:AppCommand app=%s, options=%s' % (app, sorted(options.items()))
        

from django.core.management.base import BaseCommand
import sys

class Command(BaseCommand):
    help = 'Runs the test suite for the specified applications, or the entire site if no apps are specified.'
    args = '[--verbosity] [--noinput] [appname ...]'

    requires_model_validation = False

    def handle(self, *test_labels, **options):
        from django.conf import settings
        from django.db.models import get_app, get_apps

        verbosity = options.get('verbosity', 1)
        interactive = options.get('interactive', True)
    
        test_path = settings.TEST_RUNNER.split('.')
        # Allow for Python 2.5 relative paths
        if len(test_path) > 1:
            test_module_name = '.'.join(test_path[:-1])
        else:
            test_module_name = '.'
        test_module = __import__(test_module_name, {}, {}, test_path[-1])
        test_runner = getattr(test_module, test_path[-1])

        failures = test_runner(test_labels, verbosity=verbosity, interactive=interactive)
        if failures:
            sys.exit(failures)

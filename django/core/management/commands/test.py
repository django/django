from django.core.management.base import BaseCommand
from optparse import make_option
import sys

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--failfast', action='store_true', dest='failfast', default=False,
            help='Tells Django to stop running the test suite after first failed test.')
    )
    help = 'Runs the test suite for the specified applications, or the entire site if no apps are specified.'
    args = '[appname ...]'

    requires_model_validation = False

    def handle(self, *test_labels, **options):
        from django.conf import settings
        from django.test.utils import get_runner

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)
        failfast = options.get('failfast', False)
        test_runner = get_runner(settings)

        # Some custom test runners won't accept the failfast flag, so let's make sure they accept it before passing it to them
        if 'failfast' in test_runner.func_code.co_varnames:
            failures = test_runner(test_labels, verbosity=verbosity, interactive=interactive,
                                   failfast=failfast)
        else:
            failures = test_runner(test_labels, verbosity=verbosity, interactive=interactive)

        if failures:
            sys.exit(bool(failures))

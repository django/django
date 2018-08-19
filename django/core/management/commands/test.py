import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.utils import get_command_line_option
from django.test.utils import get_runner


class Command(BaseCommand):
    help = 'Discover and run tests in the specified modules or the current directory.'

    # DiscoverRunner runs the checks after databases are set up.
    requires_system_checks = False
    test_runner = None

    def run_from_argv(self, argv):
        """
        Pre-parse the command line to extract the value of the --testrunner
        option. This allows a test runner to define additional command line
        arguments.
        """
        self.test_runner = get_command_line_option(argv, '--testrunner')
        super().run_from_argv(argv)

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='test_label', nargs='*',
            help='Module paths to test; can be modulename, modulename.TestCase or modulename.TestCase.test_method'
        )
        parser.add_argument(
            '--noinput', '--no-input', action='store_false', dest='interactive',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '--failfast', action='store_true',
            help='Tells Django to stop running the test suite after first failed test.',
        )
        parser.add_argument(
            '--testrunner',
            help='Tells Django to use specified test runner class instead of '
                 'the one specified by the TEST_RUNNER setting.',
        )
        # Allow the test runner to add commandline arguments, which are shown in a distinct section in --help output
        test_runner_class = get_runner(settings, self.test_runner)
        title = 'options specific to the "{}" testrunner'.format(self.test_runner)
        group = parser.add_argument_group(title)
        if hasattr(test_runner_class, 'add_arguments'):
            test_runner_class.add_arguments(group)

        # Show this section even when empty (by adding a description), in order to let the user see that other test
        # runners might have additional options.
        if not group._group_actions:
            group.description = "This test runner has no additional options."

    def handle(self, *test_labels, **options):
        TestRunner = get_runner(settings, options['testrunner'])

        test_runner = TestRunner(**options)
        failures = test_runner.run_tests(test_labels)

        if failures:
            sys.exit(1)

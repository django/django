from optparse import make_option

from django.core.management.commands.test import Command as TestCommand


class Command(TestCommand):
    help = "Test optparse compatibility when extending an internal command."

    option_list = TestCommand.option_list + (
        make_option("-s", "--style", default="Rock'n'Roll"),
        make_option("-x", "--example")
    )

    def handle(self, *args, **options):
        options["example"]
        # BaseCommand default option is available
        options['verbosity']
        assert isinstance(options['verbosity'], int), "verbosity option is not int, but %s" % type(options['verbosity'])
        self.stdout.write("All right, let's dance %s." % options["style"])

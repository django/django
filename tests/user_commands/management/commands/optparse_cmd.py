from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test optparse compatibility."
    args = ''

    option_list = BaseCommand.option_list + (
        make_option("-s", "--style", default="Rock'n'Roll"),
        make_option("-x", "--example")
    )

    def handle(self, *args, **options):
        options["example"]
        # BaseCommand default option is available
        options['verbosity']
        assert isinstance(options['verbosity'], int), "verbosity option is not int, but %s" % type(options['verbosity'])
        self.stdout.write("All right, let's dance %s." % options["style"])

import os
from optparse import make_option
from django.core.management.base import LabelCommand

from django.contrib.staticfiles import finders

class Command(LabelCommand):
    help = "Finds the absolute paths for the given static file(s)."
    args = "[file ...]"
    label = 'static file'
    option_list = LabelCommand.option_list + (
        make_option('--first', action='store_false', dest='all', default=True,
                    help="Only return the first match for each static file."),
    )

    def handle_label(self, path, **options):
        verbosity = int(options.get('verbosity', 1))
        result = finders.find(path, all=options['all'])
        if result:
            output = '\n  '.join((os.path.realpath(path) for path in result))
            self.stdout.write("Found %r here:\n  %s\n" % (path, output))
        else:
            if verbosity >= 1:
                self.stdout.write("No matching file found for %r.\n" % path)

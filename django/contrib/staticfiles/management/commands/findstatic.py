from __future__ import unicode_literals

import os
from optparse import make_option
from django.core.management.base import LabelCommand
from django.utils.encoding import smart_text

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
        path = smart_text(path)
        if result:
            if not isinstance(result, (list, tuple)):
                result = [result]
            output = '\n  '.join(
                (smart_text(os.path.realpath(path)) for path in result))
            self.stdout.write("Found '%s' here:\n  %s" % (path, output))
        else:
            if verbosity >= 1:
                self.stderr.write("No matching file found for '%s'." % path)

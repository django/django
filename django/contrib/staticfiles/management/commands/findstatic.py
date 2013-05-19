from __future__ import unicode_literals

import os
from optparse import make_option
from django.core.management.base import LabelCommand
from django.utils.encoding import force_text

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
        path = force_text(path)
        if result:
            if not isinstance(result, (list, tuple)):
                result = [result]
            result = (force_text(os.path.realpath(path)) for path in result)
            if verbosity >= 1:
                output = '\n  '.join(result)
                return "Found '%s' here:\n  %s" % (path, output)
            else:
                return '\n'.join(result)
        else:
            if verbosity >= 1:
                self.stderr.write("No matching file found for '%s'." % path)

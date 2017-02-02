import os

from django.contrib.staticfiles import finders
from django.core.management.base import LabelCommand
from django.utils.encoding import force_text


class Command(LabelCommand):
    help = "Finds the absolute paths for the given static file(s)."
    label = 'staticfile'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--first', action='store_false', dest='all',
            default=True,
            help="Only return the first match for each static file.",
        )

    def handle_label(self, path, **options):
        verbosity = options['verbosity']
        result = finders.find(path, all=options['all'])
        path = force_text(path)
        if verbosity >= 2:
            searched_locations = (
                "\nLooking in the following locations:\n  %s" %
                "\n  ".join(force_text(location) for location in finders.searched_locations)
            )
        else:
            searched_locations = ''
        if result:
            if not isinstance(result, (list, tuple)):
                result = [result]
            result = (force_text(os.path.realpath(path)) for path in result)
            if verbosity >= 1:
                file_list = '\n  '.join(result)
                return ("Found '%s' here:\n  %s%s" %
                        (path, file_list, searched_locations))
            else:
                return '\n'.join(result)
        else:
            message = ["No matching file found for '%s'." % path]
            if verbosity >= 2:
                message.append(searched_locations)
            if verbosity >= 1:
                self.stderr.write('\n'.join(message))

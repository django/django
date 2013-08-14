from __future__ import unicode_literals

import sys

from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Checks your configuration's compatibility with this version " + \
           "of Django."

    def handle_noargs(self, **options):
        sys.stdout.write("Sorry -- not implemented yet.")

from __future__ import unicode_literals
import warnings

from django.core.compat_checks.base import check_compatibility
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = u"Checks your configuration's compatibility with this version " + \
           u"of Django."

    def handle_noargs(self, **options):
        for message in check_compatibility():
            warnings.warn(message)

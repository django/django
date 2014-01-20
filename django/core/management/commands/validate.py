# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from django.core.management.commands.check import Command as CheckCommand


class Command(CheckCommand):
    help = 'Deprecated. Use "check" command instead. ' + CheckCommand.help

    def handle_noargs(self, **options):
        warnings.warn('"validate" has been deprecated in favour of "check".',
            PendingDeprecationWarning)
        super(Command, self).handle_noargs(**options)

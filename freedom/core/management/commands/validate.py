# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from freedom.core.management.commands.check import Command as CheckCommand
from freedom.utils.deprecation import RemovedInFreedom19Warning


class Command(CheckCommand):
    help = 'Deprecated. Use "check" command instead. ' + CheckCommand.help

    def handle_noargs(self, **options):
        warnings.warn('"validate" has been deprecated in favor of "check".',
            RemovedInFreedom19Warning)
        super(Command, self).handle_noargs(**options)

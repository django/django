# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from django.core.management.commands.check import Command as CheckCommand
from django.utils.deprecation import RemovedInDjango19Warning


class Command(CheckCommand):
    help = 'Deprecated. Use "check" command instead. ' + CheckCommand.help

    def handle(self, **options):
        warnings.warn('"validate" has been deprecated in favor of "check".',
            RemovedInDjango19Warning)
        super(Command, self).handle(**options)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.secret_key import generate_secret_key, create_secret_key_file

import os
import sys


class Command(BaseCommand):
    help = "Generates and outputs a random secret key to a file or stdout."
    requires_system_checks = False
    can_import_settings = False
    leave_locale_alone = True

    def add_arguments(self, parser):
        parser.add_argument('outfile', nargs='+')

    def handle(self, *args, **options):
        secret_key = generate_secret_key()

        for outfile in options['outfile']:
            if outfile == '-':
                self.stdout.write(secret_key)
                sys.exit(0)

            create_secret_key_file(outfile, secret_key)

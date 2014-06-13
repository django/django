# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.secret_key import generate_secret_key, create_secret_key_file

import os


class Command(BaseCommand):
    help = "Generates and outputs a random secret key to a file or stdout."
    args = "[output_file]"

    requires_system_checks = False

    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    # Can't perform any active locale changes during this command, because
    # setting might not be available at all.
    leave_locale_alone = True

    def handle(self, *output_file, **options):
        try:
            output_file = output_file[0]
        except IndexError:
            raise CommandError("You must specify a file path.")

        if output_file == '-':
            self.stdout.write(generate_secret_key())
            return

        create_secret_key_file(output_file)

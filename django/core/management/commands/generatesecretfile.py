# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import create_secret_key_file


class Command(BaseCommand):
    help = "Generates and outputs a random secret key to a file."
    args = "[output_file]"

    requires_system_checks = False

    def handle(self, *output_file, **options):
        try:
            output_file = output_file[0]
        except IndexError:
            output_file = None

        try:
            create_secret_key_file(output_file)
        except IOError:
            raise CommandError("Unable to open file for writing.")

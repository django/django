# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.utils.crypto import generate_secret_key


class Command(BaseCommand):
    help = "Generates and outputs a random secret ket to stdout."

    requires_system_checks = False

    def handle(self, **options):
        self.stdout.write(generate_secret_key())

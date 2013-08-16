# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Uses the system check framework to validate entire Django project."

    requires_system_checks = False

    def handle_noargs(self, **options):
        self.check(display_num_errors=True)

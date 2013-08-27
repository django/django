# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Uses the system check framework to validate entire Django project."

    requires_system_checks = False

    option_list = BaseCommand.option_list + (
        make_option('--tag', action='append', dest='tags',
            help='Run only checks labeled with given tag.'),
    )

    def handle(self, *apps, **options):
        apps = apps or None  # If apps is an empty list, replace with None
        self.check(apps=apps, display_num_errors=True)

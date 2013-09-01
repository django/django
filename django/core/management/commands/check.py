# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from optparse import make_option

from django.core import checks
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Uses the system check framework to validate entire Django project."

    requires_system_checks = False

    option_list = BaseCommand.option_list + (
        make_option('--tag', '-t', action='append', dest='tags',
            help='Run only checks labeled with given tag.'),
    )

    def handle(self, *apps, **options):
        apps = apps or None  # If apps is an empty list, replace with None
        tags = options.get('tags', None)
        if tags and any(not checks.tag_exists(tag) for tag in tags):
            invalid_tag = next(tag for tag in tags if not checks.tag_exists(tag))
            raise CommandError('There is no system check labeled with "%s" tag.' % invalid_tag)
        self.check(apps=apps, tags=tags, display_num_errors=True)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from optparse import make_option

from django.apps import apps
from django.core import checks
from django.core.checks.registry import registry
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Checks the entire Django project for potential problems."

    requires_system_checks = False

    option_list = BaseCommand.option_list + (
        make_option('--tag', '-t', action='append', dest='tags',
            help='Run only checks labeled with given tag.'),
        make_option('--list-tags', action='store_true', dest='list_tags',
            help='List available tags.'),
    )

    def handle(self, *app_labels, **options):
        if options.get('list_tags'):
            self.stdout.write('\n'.join(sorted(registry.tags_available())))
            return

        if app_labels:
            app_configs = [apps.get_app_config(app_label) for app_label in app_labels]
        else:
            app_configs = None

        tags = options.get('tags', None)
        if tags and any(not checks.tag_exists(tag) for tag in tags):
            invalid_tag = next(tag for tag in tags if not checks.tag_exists(tag))
            raise CommandError('There is no system check with the "%s" tag.' % invalid_tag)

        self.check(app_configs=app_configs, tags=tags, display_num_errors=True)

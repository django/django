# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.core.checks import register, Warning
from django.apps import apps


def import_settings():
    from django.conf import settings
    return settings


@register('settings')
def check_fixture_dirs_has_non_unique_items(**kwargs):
    settings = import_settings()
    fixture_dirs = settings.FIXTURE_DIRS

    if fixture_dirs and len(fixture_dirs) != len(set(fixture_dirs)):
        return [
            Warning(
                "settings.FIXTURE_DIRS has duplications.",
                hint="Each directory path in FIXTURE_DIRS setting should be "
                "unique in order to avoid repeated fixture loading.",
                obj="",
                id='settings.W001',
            )]
    return []


@register('settings')
def check_fixture_dirs_contains_default_fixture_paths(**kwargs):
    settings = import_settings()
    fixture_dirs = settings.FIXTURE_DIRS
    project_app_configs = apps.get_app_configs()
    errors = []

    for project_app in project_app_configs:
        project_app_dir = os.path.join(project_app.path, 'fixtures')

        if project_app_dir in fixture_dirs:
            errors.append(
                Warning(
                    "'%s' is a default fixture directory for app '%s' and should "
                    "not be listed in settings.FIXTURE_DIRS in order to "
                    "avoid repeated fixture loading."
                    % (project_app_dir, project_app.label),
                    hint="",
                    obj="",
                    id='settings.W002',
                ))
    return errors

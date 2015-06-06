# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

from . import Error, Tags, register

E001 = Error(
    "You have 'APP_DIRS': True in your TEMPLATES, while explicitly specifying"
    "the template loaders. Either remove APP_DIRS or remove the "
    "'loaders' configuration.",
    id='templates.E001',
)


@register(Tags.templates)
def check_setting_app_dirs_loaders(app_configs, **kwargs):
    passed_check = True
    for conf in settings.TEMPLATES:
        if not conf.get('APP_DIRS'):
            continue
        if 'loaders' in conf.get('OPTIONS', {}):
            passed_check = False
    return [] if passed_check else [E001]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from . import Warning, register


@register('models')
def check_all_models(apps=None, **kwargs):
    from django.db import models

    errors = [model.check(**kwargs)
        for model in models.get_models(**kwargs)
        if apps is None or model._meta.app_label in apps]
    return list(chain(*errors))

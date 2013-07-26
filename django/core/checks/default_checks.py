# -*- coding: utf-8 -*-
from __future__ import unicode_literals


# This check is registered in __init__.py file.
def check_all_models(**kwargs):
    from django.db import models

    errors = []
    for cls in models.get_models(include_swapped=True):
        errors.extend(cls.check())
    return errors

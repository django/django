# -*- encoding: utf-8 -*-
from __future__ import unicode_literals


def get_validation_errors(app=None):
    """
    Validates all models that are part of the specified app. If no app name is
    provided, validates all models of all installed apps. Writes errors, if any,
    to outfile. Returns number of errors.
    """
    from django.db import models

    errors = []
    for cls in models.get_models(app, include_swapped=True):
        errors.extend(cls.check())
    return errors

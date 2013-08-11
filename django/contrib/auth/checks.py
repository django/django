# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import checks


def check_user_model(**kwargs):
    from django.conf import settings
    from django.db import models

    errors = []
    app_name, model_name = settings.AUTH_USER_MODEL.split('.')

    #try:
    cls = models.get_model(app_name, model_name)
    #except Exception as e:
    #    pass  #import ipdb; ipdb.set_trace()

    # Check that REQUIRED_FIELDS is a list
    if not isinstance(cls.REQUIRED_FIELDS, (list, tuple)):
        errors.append(
            checks.Error(
                'The REQUIRED_FIELDS must be a list or tuple.',
                hint=None,
                obj=cls,
            )
        )


    # Check that the USERNAME FIELD isn't included in REQUIRED_FIELDS.
    if cls.USERNAME_FIELD in cls.REQUIRED_FIELDS:
        errors.append(
            checks.Error(
                'The field named as the USERNAME_FIELD '
                    'must not be included in REQUIRED_FIELDS '
                    'on a custom user model.',
                hint=None,
                obj=cls,
            )
        )


    # Check that the username field is unique
    if not cls._meta.get_field(cls.USERNAME_FIELD).unique:
        if settings.AUTHENTICATION_BACKENDS == \
                ('django.contrib.auth.backends.ModelBackend',):
            errors.append(
                checks.Error(
                    'The %s.%s field must be unique because it is '
                        'pointed to by USERNAME_FIELD.'
                        % (cls._meta.object_name, cls.USERNAME_FIELD),
                    hint=None,
                    obj=cls,
                )
            )
        else:
            errors.append(
                checks.Warning(
                    'The %s.%s field is pointed to by USERNAME_FIELD, '
                        'but it is not unique. Ensure that '
                        'your authentication backend can handle '
                        'non-unique usernames.'
                        % (cls._meta.object_name, cls.USERNAME_FIELD),
                    hint=None,
                    obj=cls,
                )
            )

    return errors

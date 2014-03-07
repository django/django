# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.conf import settings
from django.core import checks


def check_user_model(**kwargs):
    errors = []

    cls = apps.get_model(settings.AUTH_USER_MODEL)

    # Check that REQUIRED_FIELDS is a list
    if not isinstance(cls.REQUIRED_FIELDS, (list, tuple)):
        errors.append(
            checks.Error(
                "'REQUIRED_FIELDS' must be a list or tuple.",
                hint=None,
                obj=cls,
                id='auth.E001',
            )
        )

    # Check that the USERNAME FIELD isn't included in REQUIRED_FIELDS.
    if cls.USERNAME_FIELD in cls.REQUIRED_FIELDS:
        errors.append(
            checks.Error(
                ("The field named as the 'USERNAME_FIELD' "
                 "for a custom user model must not be included in 'REQUIRED_FIELDS'."),
                hint=None,
                obj=cls,
                id='auth.E002',
            )
        )

    # Check that the username field is unique
    if not cls._meta.get_field(cls.USERNAME_FIELD).unique:
        if (settings.AUTHENTICATION_BACKENDS ==
                ('django.contrib.auth.backends.ModelBackend',)):
            errors.append(
                checks.Error(
                    "'%s.%s' must be unique because it is named as the 'USERNAME_FIELD'." % (
                        cls._meta.object_name, cls.USERNAME_FIELD
                    ),
                    hint=None,
                    obj=cls,
                    id='auth.E003',
                )
            )
        else:
            errors.append(
                checks.Warning(
                    "'%s.%s' is named as the 'USERNAME_FIELD', but it is not unique." % (
                        cls._meta.object_name, cls.USERNAME_FIELD
                    ),
                    hint=('Ensure that your authentication backend(s) can handle '
                          'non-unique usernames.'),
                    obj=cls,
                    id='auth.W004',
                )
            )

    return errors

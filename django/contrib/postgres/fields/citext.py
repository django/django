import warnings

from django.db.models import CharField, EmailField, TextField
from django.test.utils import ignore_warnings
from django.utils.deprecation import RemovedInDjango51Warning

__all__ = ["CICharField", "CIEmailField", "CIText", "CITextField"]


# RemovedInDjango51Warning.
class CIText:
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "django.contrib.postgres.fields.CIText mixin is deprecated.",
            RemovedInDjango51Warning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return f"CI{super().get_internal_type()}"

    def db_type(self, connection):
        return "citext"


class CICharField(CIText, CharField):
    system_check_deprecated_details = {
        "msg": (
            "django.contrib.postgres.fields.CICharField is deprecated. Support for it "
            "(except in historical migrations) will be removed in Django 5.1."
        ),
        "hint": (
            'Use CharField(db_collation="…") with a case-insensitive non-deterministic '
            "collation instead."
        ),
        "id": "fields.W905",
    }

    def __init__(self, *args, **kwargs):
        with ignore_warnings(category=RemovedInDjango51Warning):
            super().__init__(*args, **kwargs)


class CIEmailField(CIText, EmailField):
    system_check_deprecated_details = {
        "msg": (
            "django.contrib.postgres.fields.CIEmailField is deprecated. Support for it "
            "(except in historical migrations) will be removed in Django 5.1."
        ),
        "hint": (
            'Use EmailField(db_collation="…") with a case-insensitive '
            "non-deterministic collation instead."
        ),
        "id": "fields.W906",
    }

    def __init__(self, *args, **kwargs):
        with ignore_warnings(category=RemovedInDjango51Warning):
            super().__init__(*args, **kwargs)


class CITextField(CIText, TextField):
    system_check_deprecated_details = {
        "msg": (
            "django.contrib.postgres.fields.CITextField is deprecated. Support for it "
            "(except in historical migrations) will be removed in Django 5.1."
        ),
        "hint": (
            'Use TextField(db_collation="…") with a case-insensitive non-deterministic '
            "collation instead."
        ),
        "id": "fields.W907",
    }

    def __init__(self, *args, **kwargs):
        with ignore_warnings(category=RemovedInDjango51Warning):
            super().__init__(*args, **kwargs)

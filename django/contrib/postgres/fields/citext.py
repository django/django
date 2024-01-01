from django.db.models import CharField, EmailField, TextField

__all__ = ["CICharField", "CIEmailField", "CITextField"]


class CICharField(CharField):
    system_check_removed_details = {
        "msg": (
            "django.contrib.postgres.fields.CICharField is removed except for support "
            "in historical migrations."
        ),
        "hint": (
            'Use CharField(db_collation="…") with a case-insensitive non-deterministic '
            "collation instead."
        ),
        "id": "fields.E905",
    }


class CIEmailField(EmailField):
    system_check_removed_details = {
        "msg": (
            "django.contrib.postgres.fields.CIEmailField is removed except for support "
            "in historical migrations."
        ),
        "hint": (
            'Use EmailField(db_collation="…") with a case-insensitive '
            "non-deterministic collation instead."
        ),
        "id": "fields.E906",
    }


class CITextField(TextField):
    system_check_removed_details = {
        "msg": (
            "django.contrib.postgres.fields.CITextField is removed except for support "
            "in historical migrations."
        ),
        "hint": (
            'Use TextField(db_collation="…") with a case-insensitive non-deterministic '
            "collation instead."
        ),
        "id": "fields.E907",
    }

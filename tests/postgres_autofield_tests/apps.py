from django.apps import AppConfig

from .fields import FieldForTesting


def get_class_full_path(cls):
    return f"{cls.__module__}.{cls.__name__}"


class UUIDv4AutoAppConfig(AppConfig):
    name = "postgres_autofield_tests"

    default_auto_field = get_class_full_path(FieldForTesting)

from itertools import chain

from django.apps import apps


def check_generic_foreign_keys(app_configs=None, **kwargs):
    from .fields import GenericForeignKey

    if app_configs is None:
        models = apps.get_models()
    else:
        models = chain.from_iterable(app_config.get_models() for app_config in app_configs)
    errors = []
    fields = (
        obj for model in models for obj in vars(model).values()
        if isinstance(obj, GenericForeignKey)
    )
    for field in fields:
        errors.extend(field.check())
    return errors

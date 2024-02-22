from itertools import chain

from django.apps import apps
from django.core.checks import Error


def check_model_name_lengths(app_configs=None, **kwargs):
    if app_configs is None:
        models = apps.get_models()
    else:
        models = chain.from_iterable(
            app_config.get_models() for app_config in app_configs
        )
    errors = []
    for model in models:
        if len(model._meta.model_name) > 100:
            errors.append(
                Error(
                    "Model names must be at most 100 characters (got %d)."
                    % (len(model._meta.model_name),),
                    obj=model,
                    id="contenttypes.E005",
                )
            )
    return errors

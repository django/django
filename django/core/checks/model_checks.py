# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import types

from django.apps import apps
from django.core.checks import Error, Tags, register


@register(Tags.models)
def check_all_models(app_configs=None, **kwargs):
    errors = []
    for model in apps.get_models():
        if app_configs is None or model._meta.app_config in app_configs:
            if not inspect.ismethod(model.check):
                errors.append(
                    Error(
                        "The '%s.check()' class method is "
                        "currently overridden by %r." % (
                            model.__name__, model.check),
                        hint=None,
                        obj=model,
                        id='models.E020'
                    )
                )
            else:
                errors.extend(model.check(**kwargs))
    return errors


@register(Tags.models, Tags.signals)
def check_model_signals(app_configs=None, **kwargs):
    """
    Ensure lazily referenced model signals senders are installed.
    """
    # Avoid circular import
    from django.db import models

    errors = []
    for name in dir(models.signals):
        obj = getattr(models.signals, name)
        if isinstance(obj, models.signals.ModelSignal):
            for reference, receivers in obj.unresolved_references.items():
                for receiver, _, _ in receivers:
                    # The receiver is either a function or an instance of class
                    # defining a `__call__` method.
                    if isinstance(receiver, types.FunctionType):
                        description = "The '%s' function" % receiver.__name__
                    else:
                        description = "An instance of the '%s' class" % receiver.__class__.__name__
                    errors.append(
                        Error(
                            "%s was connected to the '%s' signal "
                            "with a lazy reference to the '%s' sender, "
                            "which has not been installed." % (
                                description, name, '.'.join(reference)
                            ),
                            obj=receiver.__module__,
                            hint=None,
                            id='signals.E001'
                        )
                    )
    return errors

import warnings
from functools import partial

from django.db.models.utils import make_model_tuple
from django.dispatch import Signal
from django.utils.deprecation import RemovedInDjango20Warning


class_prepared = Signal(providing_args=["class"])


class ModelSignal(Signal):
    """
    Signal subclass that allows the sender to be lazily specified as a string
    of the `app_label.ModelName` form.
    """
    def _lazy_method(self, method, apps, receiver, sender, **kwargs):
        # This partial takes a single optional argument named "sender".
        partial_method = partial(method, receiver, **kwargs)
        # import models here to avoid a circular import
        from django.db import models
        if isinstance(sender, models.Model) or sender is None:
            # Skip lazy_model_operation to get a return value for disconnect()
            return partial_method(sender)
        apps = apps or models.base.Options.default_apps
        apps.lazy_model_operation(partial_method, make_model_tuple(sender))

    def connect(self, receiver, sender=None, weak=True, dispatch_uid=None, apps=None):
        self._lazy_method(super(ModelSignal, self).connect, apps, receiver, sender, dispatch_uid=dispatch_uid)

    def disconnect(self, receiver=None, sender=None, weak=None, dispatch_uid=None, apps=None):
        if weak is not None:
            warnings.warn("Passing `weak` to disconnect has no effect.", RemovedInDjango20Warning, stacklevel=2)
        return self._lazy_method(
            super(ModelSignal, self).disconnect, apps, receiver, sender, dispatch_uid=dispatch_uid
        )


pre_init = ModelSignal(providing_args=["instance", "args", "kwargs"], use_caching=True)
post_init = ModelSignal(providing_args=["instance"], use_caching=True)

pre_save = ModelSignal(providing_args=["instance", "raw", "using", "update_fields"],
                       use_caching=True)
post_save = ModelSignal(providing_args=["instance", "raw", "created", "using", "update_fields"], use_caching=True)

pre_delete = ModelSignal(providing_args=["instance", "using"], use_caching=True)
post_delete = ModelSignal(providing_args=["instance", "using"], use_caching=True)

m2m_changed = ModelSignal(
    providing_args=["action", "instance", "reverse", "model", "pk_set", "using"],
    use_caching=True,
)

pre_migrate = Signal(providing_args=["app_config", "verbosity", "interactive", "using", "apps", "plan"])
post_migrate = Signal(providing_args=["app_config", "verbosity", "interactive", "using", "apps", "plan"])

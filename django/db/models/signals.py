from functools import partial

from django.db.models.utils import make_model_tuple
from django.dispatch import Signal


class_prepared = Signal(providing_args=["class"])


class ModelSignal(Signal):
    """
    Signal subclass that allows the sender to be lazily specified as a string
    of the `app_label.ModelName` form.
    """
    def connect(self, receiver, sender=None, weak=True, dispatch_uid=None, apps=None):
        # Takes a single optional argument named "sender"
        connect = partial(super(ModelSignal, self).connect, receiver, weak=weak, dispatch_uid=dispatch_uid)
        models = [make_model_tuple(sender)] if sender else []
        if not apps:
            from django.db.models.base import Options
            apps = sender._meta.apps if hasattr(sender, '_meta') else Options.default_apps
        apps.lazy_model_operation(connect, *models)


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

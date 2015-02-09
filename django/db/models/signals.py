from django.apps import apps
from django.dispatch import Signal
from django.utils import six


class_prepared = Signal(providing_args=["class"])


class ModelSignal(Signal):
    """
    Signal subclass that allows the sender to be lazily specified as a string
    of the `app_label.ModelName` form.
    """

    def __init__(self, *args, **kwargs):
        super(ModelSignal, self).__init__(*args, **kwargs)
        self.unresolved_references = {}
        class_prepared.connect(self._resolve_references)

    def _resolve_references(self, sender, **kwargs):
        opts = sender._meta
        reference = (opts.app_label, opts.object_name)
        try:
            receivers = self.unresolved_references.pop(reference)
        except KeyError:
            pass
        else:
            for receiver, weak, dispatch_uid in receivers:
                super(ModelSignal, self).connect(
                    receiver, sender=sender, weak=weak, dispatch_uid=dispatch_uid
                )

    def connect(self, receiver, sender=None, weak=True, dispatch_uid=None):
        if isinstance(sender, six.string_types):
            try:
                app_label, model_name = sender.split('.')
            except ValueError:
                raise ValueError(
                    "Specified sender must either be a model or a "
                    "model name of the 'app_label.ModelName' form."
                )
            try:
                sender = apps.get_registered_model(app_label, model_name)
            except LookupError:
                ref = (app_label, model_name)
                refs = self.unresolved_references.setdefault(ref, [])
                refs.append((receiver, weak, dispatch_uid))
                return
        super(ModelSignal, self).connect(
            receiver, sender=sender, weak=weak, dispatch_uid=dispatch_uid
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

pre_migrate = Signal(providing_args=["app_config", "verbosity", "interactive", "using"])
post_migrate = Signal(providing_args=["app_config", "verbosity", "interactive", "using"])

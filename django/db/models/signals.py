import warnings

from django.dispatch import Signal

class_prepared = Signal(providing_args=["class"])

pre_init = Signal(providing_args=["instance", "args", "kwargs"], use_caching=True)
post_init = Signal(providing_args=["instance"], use_caching=True)

pre_save = Signal(providing_args=["instance", "raw", "using", "update_fields"],
                 use_caching=True)
post_save = Signal(providing_args=["instance", "raw", "created", "using", "update_fields"], use_caching=True)

pre_delete = Signal(providing_args=["instance", "using"], use_caching=True)
post_delete = Signal(providing_args=["instance", "using"], use_caching=True)

pre_migrate = Signal(providing_args=["app", "create_models", "verbosity", "interactive", "using"])
post_migrate = Signal(providing_args=["class", "app", "created_models", "verbosity", "interactive", "using"])


class DeprecatedSignal(Signal):
    def __init__(self, *args, **kwargs):
        self.deprecation = kwargs.pop('deprecation')
        super(DeprecatedSignal, self).__init__(*args, **kwargs)

    def connect(self, *args, **kwargs):
        warnings.warn(
            "%s signal is deprecated and will be removed in Django 1.9, "
            "use %s instead." % self.deprecation,
            PendingDeprecationWarning, stacklevel=2
        )
        super(DeprecatedSignal, self).connect(*args, **kwargs)


pre_syncdb = DeprecatedSignal(
    providing_args=["app", "create_models", "verbosity", "interactive", "db"],
    deprecation=('pre_syncdb', 'pre_migrate'))

post_syncdb = DeprecatedSignal(
    providing_args=["class", "app", "created_models", "verbosity", "interactive", "db"],
    deprecation=('post_syncdb', 'post_migrate'))

m2m_changed = Signal(providing_args=["action", "instance", "reverse", "model", "pk_set", "using"], use_caching=True)

from django.dispatch import Signal

class_prepared = Signal(providing_args=["class"])

pre_init = Signal(providing_args=["instance", "args", "kwargs"], use_caching=True)
post_init = Signal(providing_args=["instance"], use_caching=True)

pre_save = Signal(providing_args=["instance", "raw", "using", "update_fields"],
                 use_caching=True)
post_save = Signal(providing_args=["instance", "raw", "created", "using", "update_fields"], use_caching=True)

pre_delete = Signal(providing_args=["instance", "using"], use_caching=True)
post_delete = Signal(providing_args=["instance", "using"], use_caching=True)

pre_syncdb = Signal(providing_args=["app", "create_models", "verbosity", "interactive", "db"])
post_syncdb = Signal(providing_args=["class", "app", "created_models", "verbosity", "interactive", "db"])

m2m_changed = Signal(providing_args=["action", "instance", "reverse", "model", "pk_set", "using"], use_caching=True)

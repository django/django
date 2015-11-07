from django.utils.module_loading import import_string


class InvalidChannelBackendError(ValueError):
    pass


class BackendManager(object):
    """
    Takes a settings dictionary of backends and initialises them.
    """

    def __init__(self, backend_configs):
        self.configs = backend_configs
        self.backends = {}

    def make_backend(self, name):
        # Load the backend class
        try:
            backend_class = import_string(self.configs[name]['BACKEND'])
        except KeyError:
            raise InvalidChannelBackendError("No BACKEND specified for %s" % name)
        except ImportError:
            raise InvalidChannelBackendError(
                "Cannot import BACKEND %r specified for %s" % (self.configs[name]['BACKEND'], name)
            )

        # Initialise and pass config
        instance = backend_class(**{k.lower(): v for k, v in self.configs[name].items() if k != "BACKEND"})
        instance.alias = name
        return instance

    def __getitem__(self, key):
        if key not in self.backends:
            self.backends[key] = self.make_backend(key)
        return self.backends[key]

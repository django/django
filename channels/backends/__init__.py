from django.utils.module_loading import import_string


class InvalidChannelBackendError(ValueError):
    pass


class BackendManager(object):
    """
    Takes a settings dictionary of backends and initialises them.
    """

    def __init__(self, backend_configs):
        self.backends = {}
        for name, config in backend_configs.items():
            # Load the backend class
            try:
                backend_class = import_string(config['BACKEND'])
            except KeyError:
                raise InvalidChannelBackendError("No BACKEND specified for %s" % name)
            except ImportError:
                raise InvalidChannelBackendError("Cannot import BACKEND %s specified for %s" % (config['BACKEND'], name))
            # Initialise and pass config
            self.backends[name] = backend_class(**{k.lower(): v for k, v in config.items() if k != "BACKEND"})

    def __getitem__(self, key):
        return self.backends[key]

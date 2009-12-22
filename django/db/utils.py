import inspect
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

def load_backend(backend_name):
    try:
        module = import_module('.base', 'django.db.backends.%s' % backend_name)
        import warnings
        warnings.warn(
            "Short names for DATABASE_ENGINE are deprecated; prepend with 'django.db.backends.'",
            PendingDeprecationWarning
        )
        return module
    except ImportError, e:
        # Look for a fully qualified database backend name
        try:
            return import_module('.base', backend_name)
        except ImportError, e_user:
            # The database backend wasn't found. Display a helpful error message
            # listing all possible (built-in) database backends.
            backend_dir = os.path.join(os.path.dirname(__file__), 'backends')
            try:
                available_backends = [f for f in os.listdir(backend_dir)
                        if os.path.isdir(os.path.join(backend_dir, f))
                        and not f.startswith('.')]
            except EnvironmentError:
                available_backends = []
            available_backends.sort()
            if backend_name not in available_backends:
                error_msg = ("%r isn't an available database backend. \n" +
                    "Try using django.db.backends.XXX, where XXX is one of:\n    %s\n" +
                    "Error was: %s") % \
                    (backend_name, ", ".join(map(repr, available_backends)), e_user)
                raise ImproperlyConfigured(error_msg)
            else:
                raise # If there's some other error, this must be an error in Django itself.

class ConnectionDoesNotExist(Exception):
    pass

class ConnectionHandler(object):
    def __init__(self, databases):
        self.databases = databases
        self._connections = {}

    def ensure_defaults(self, alias):
        """
        Puts the defaults into the settings dictionary for a given connection
        where no settings is provided.
        """
        try:
            conn = self.databases[alias]
        except KeyError:
            raise ConnectionDoesNotExist("The connection %s doesn't exist" % alias)
        conn.setdefault('ENGINE', 'dummy')
        conn.setdefault('OPTIONS', {})
        conn.setdefault('TEST_CHARSET', None)
        conn.setdefault('TEST_COLLATION', None)
        conn.setdefault('TEST_NAME', None)
        conn.setdefault('TIME_ZONE', settings.TIME_ZONE)
        for setting in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
            conn.setdefault(setting, '')

    def __getitem__(self, alias):
        if alias in self._connections:
            return self._connections[alias]

        self.ensure_defaults(alias)
        db = self.databases[alias]
        backend = load_backend(db['ENGINE'])
        conn = backend.DatabaseWrapper(db, alias)
        self._connections[alias] = conn
        return conn

    def __iter__(self):
        return iter(self.databases)

    def all(self):
        return [self[alias] for alias in self]

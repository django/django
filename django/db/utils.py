import inspect
import os

from django.conf import settings
from django.utils.importlib import import_module

def load_backend(backend_name):
    try:
        # Most of the time, the database backend will be one of the official
        # backends that ships with Django, so look there first.
        return import_module('.base', 'django.db.backends.%s' % backend_name)
    except ImportError, e:
        raise
        # If the import failed, we might be looking for a database backend
        # distributed external to Django. So we'll try that next.
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
                error_msg = "%r isn't an available database backend. Available options are: %s\nError was: %s" % \
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
        conn.setdefault('DATABASE_ENGINE', 'dummy')
        conn.setdefault('DATABASE_OPTIONS', {})
        conn.setdefault('TEST_DATABASE_CHARSET', None)
        conn.setdefault('TEST_DATABASE_COLLATION', None)
        conn.setdefault('TEST_DATABASE_NAME', None)
        conn.setdefault('TIME_ZONE', settings.TIME_ZONE)
        for setting in ('DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD',
            'DATABASE_HOST', 'DATABASE_PORT'):
            conn.setdefault(setting, '')

    def __getitem__(self, alias):
        if alias in self._connections:
            return self._connections[alias]

        self.ensure_defaults(alias)
        db = self.databases[alias]
        backend = load_backend(db['DATABASE_ENGINE'])
        conn = backend.DatabaseWrapper(db)
        self._connections[alias] = conn
        return conn

    def __iter__(self):
        return iter(self.databases)

    def all(self):
        return [self[alias] for alias in self]

    def alias_for_connection(self, connection):
        """
        Returns the alias for the given connection object.
        """
        return self.alias_for_settings(connection.settings_dict)

    def alias_for_settings(self, settings_dict):
        """
        Returns the alias for the given settings dictionary.
        """
        for alias in self:
            conn_settings = self.databases[alias]
            if conn_settings == settings_dict:
                return alias
        return None

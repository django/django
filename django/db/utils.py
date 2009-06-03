import os

from django.utils.importlib import import_module

def load_backend(backend_name):
    try:
        # Most of the time, the database backend will be one of the official
        # backends that ships with Django, so look there first.
        return import_module('.base', 'django.db.backends.%s' % backend_name)
    except ImportError, e:
        # If the import failed, we might be looking for a database backend
        # distributed external to Django. So we'll try that next.
        try:
            return import_module('.base', backend_name)
        except ImportError, e_user:
            # The database backend wasn't found. Display a helpful error message
            # listing all possible (built-in) database backends.
            backend_dir = os.path.join(__path__[0], 'backends')
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

class ConnectionHandler(object):
    def __init__(self, databases):
        self.databases = databases
        self._connections = {}

    def check_connection(self, alias):
        conn = self.databases[alias]
        conn.setdefault('DATABASE_ENGINE', 'dummy')
        conn.setdefault('DATABASE_OPTIONS', {})
        for setting in ('DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD',
            'DATABASE_HOST', 'DATABASE_PORT'):
            conn.setdefault(setting, '')

    def __getitem__(self, alias):
        if alias in self._connections:
            return self._connections[alias]

        self.check_connection(alias)
        db = self.databases[alias]
        backend = load_backend(db['DATABASE_ENGINE'])
        conn = backend.DatabaseWrapper(db)
        self._connections[alias] = conn
        return conn

    def all(self):
        return [self[alias] for alias in self.databases]

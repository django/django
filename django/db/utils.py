import inspect
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

DEFAULT_DB_ALIAS = 'default'

# Define some exceptions that mirror the PEP249 interface.
# We will rethrow any backend-specific errors using these
# common wrappers
class DatabaseError(Exception):
    pass

class IntegrityError(DatabaseError):
    pass


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

        conn.setdefault('ENGINE', 'django.db.backends.dummy')
        if conn['ENGINE'] == 'django.db.backends.' or not conn['ENGINE']:
            conn['ENGINE'] = 'django.db.backends.dummy'
        conn.setdefault('OPTIONS', {})
        conn.setdefault('TEST_CHARSET', None)
        conn.setdefault('TEST_COLLATION', None)
        conn.setdefault('TEST_NAME', None)
        conn.setdefault('TEST_MIRROR', None)
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


class ConnectionRouter(object):
    def __init__(self, routers):
        self.routers = []
        for r in routers:
            if isinstance(r, basestring):
                try:
                    module_name, klass_name = r.rsplit('.', 1)
                    module = import_module(module_name)
                except ImportError, e:
                    raise ImproperlyConfigured('Error importing database router %s: "%s"' % (klass_name, e))
                try:
                    router_class = getattr(module, klass_name)
                except AttributeError:
                    raise ImproperlyConfigured('Module "%s" does not define a database router name "%s"' % (module, klass_name))
                else:
                    router = router_class()
            else:
                router = r
            self.routers.append(router)

    def _router_func(action):
        def _route_db(self, model, **hints):
            chosen_db = None
            for router in self.routers:
                try:
                    chosen_db = getattr(router, action)(model, **hints)
                    if chosen_db:
                        return chosen_db
                except AttributeError:
                    # If the router doesn't have a method, skip to the next one.
                    pass
            try:
                return hints['instance']._state.db or DEFAULT_DB_ALIAS
            except KeyError:
                return DEFAULT_DB_ALIAS
        return _route_db

    db_for_read = _router_func('db_for_read')
    db_for_write = _router_func('db_for_write')

    def allow_relation(self, obj1, obj2, **hints):
        for router in self.routers:
            try:
                allow = router.allow_relation(obj1, obj2, **hints)
                if allow is not None:
                    return allow
            except AttributeError:
                # If the router doesn't have a method, skip to the next one.
                pass
        return obj1._state.db == obj2._state.db

    def allow_syncdb(self, db, model):
        for router in self.routers:
            try:
                allow = router.allow_syncdb(db, model)
                if allow is not None:
                    return allow
            except AttributeError:
                # If the router doesn't have a method, skip to the next one.
                pass
        return True

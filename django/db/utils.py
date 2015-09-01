import inspect
import os
import pkgutil
import warnings
from importlib import import_module
from threading import local

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils._os import npath, upath
from django.utils.deprecation import RemovedInDjango110Warning
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

DEFAULT_DB_ALIAS = 'default'
DJANGO_VERSION_PICKLE_KEY = '_django_version'


class Error(Exception if six.PY3 else StandardError):  # NOQA: StandardError undefined on PY3
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


class DatabaseErrorWrapper(object):
    """
    Context manager and decorator that re-throws backend-specific database
    exceptions using Django's common wrappers.
    """

    def __init__(self, wrapper):
        """
        wrapper is a database wrapper.

        It must have a Database attribute defining PEP-249 exceptions.
        """
        self.wrapper = wrapper

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            return
        for dj_exc_type in (
                DataError,
                OperationalError,
                IntegrityError,
                InternalError,
                ProgrammingError,
                NotSupportedError,
                DatabaseError,
                InterfaceError,
                Error,
        ):
            db_exc_type = getattr(self.wrapper.Database, dj_exc_type.__name__)
            if issubclass(exc_type, db_exc_type):
                dj_exc_value = dj_exc_type(*exc_value.args)
                dj_exc_value.__cause__ = exc_value
                # Only set the 'errors_occurred' flag for errors that may make
                # the connection unusable.
                if dj_exc_type not in (DataError, IntegrityError):
                    self.wrapper.errors_occurred = True
                six.reraise(dj_exc_type, dj_exc_value, traceback)

    def __call__(self, func):
        # Note that we are intentionally not using @wraps here for performance
        # reasons. Refs #21109.
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner


def load_backend(backend_name):
    """
    Return a database backend's "base" module given a fully qualified database
    backend name, or raise an error if it doesn't exist.
    """
    # This backend was renamed in Django 1.9.
    if backend_name == 'django.db.backends.postgresql_psycopg2':
        backend_name = 'django.db.backends.postgresql'

    try:
        return import_module('%s.base' % backend_name)
    except ImportError as e_user:
        # The database backend wasn't found. Display a helpful error message
        # listing all possible (built-in) database backends.
        backend_dir = os.path.join(os.path.dirname(upath(__file__)), 'backends')
        try:
            builtin_backends = [
                name for _, name, ispkg in pkgutil.iter_modules([npath(backend_dir)])
                if ispkg and name not in {'base', 'dummy', 'postgresql_psycopg2'}
            ]
        except EnvironmentError:
            builtin_backends = []
        if backend_name not in ['django.db.backends.%s' % b for b in
                                builtin_backends]:
            backend_reprs = map(repr, sorted(builtin_backends))
            error_msg = ("%r isn't an available database backend.\n"
                         "Try using 'django.db.backends.XXX', where XXX "
                         "is one of:\n    %s\nError was: %s" %
                         (backend_name, ", ".join(backend_reprs), e_user))
            raise ImproperlyConfigured(error_msg)
        else:
            # If there's some other error, this must be an error in Django
            raise


class ConnectionDoesNotExist(Exception):
    pass


class ConnectionHandler(object):
    def __init__(self, databases=None):
        """
        databases is an optional dictionary of database definitions (structured
        like settings.DATABASES).
        """
        self._databases = databases
        self._connections = local()

    @cached_property
    def databases(self):
        if self._databases is None:
            self._databases = settings.DATABASES
        if self._databases == {}:
            self._databases = {
                DEFAULT_DB_ALIAS: {
                    'ENGINE': 'django.db.backends.dummy',
                },
            }
        if self._databases[DEFAULT_DB_ALIAS] == {}:
            self._databases[DEFAULT_DB_ALIAS]['ENGINE'] = 'django.db.backends.dummy'

        if DEFAULT_DB_ALIAS not in self._databases:
            raise ImproperlyConfigured("You must define a '%s' database" % DEFAULT_DB_ALIAS)
        return self._databases

    def ensure_defaults(self, alias):
        """
        Puts the defaults into the settings dictionary for a given connection
        where no settings is provided.
        """
        try:
            conn = self.databases[alias]
        except KeyError:
            raise ConnectionDoesNotExist("The connection %s doesn't exist" % alias)

        conn.setdefault('ATOMIC_REQUESTS', False)
        conn.setdefault('AUTOCOMMIT', True)
        conn.setdefault('ENGINE', 'django.db.backends.dummy')
        if conn['ENGINE'] == 'django.db.backends.' or not conn['ENGINE']:
            conn['ENGINE'] = 'django.db.backends.dummy'
        conn.setdefault('CONN_MAX_AGE', 0)
        conn.setdefault('OPTIONS', {})
        conn.setdefault('TIME_ZONE', None)
        for setting in ['NAME', 'USER', 'PASSWORD', 'HOST', 'PORT']:
            conn.setdefault(setting, '')

    def prepare_test_settings(self, alias):
        """
        Makes sure the test settings are available in the 'TEST' sub-dictionary.
        """
        try:
            conn = self.databases[alias]
        except KeyError:
            raise ConnectionDoesNotExist("The connection %s doesn't exist" % alias)

        test_settings = conn.setdefault('TEST', {})
        for key in ['CHARSET', 'COLLATION', 'NAME', 'MIRROR']:
            test_settings.setdefault(key, None)

    def __getitem__(self, alias):
        if hasattr(self._connections, alias):
            return getattr(self._connections, alias)

        self.ensure_defaults(alias)
        self.prepare_test_settings(alias)
        db = self.databases[alias]
        backend = load_backend(db['ENGINE'])
        conn = backend.DatabaseWrapper(db, alias)
        setattr(self._connections, alias, conn)
        return conn

    def __setitem__(self, key, value):
        setattr(self._connections, key, value)

    def __delitem__(self, key):
        delattr(self._connections, key)

    def __iter__(self):
        return iter(self.databases)

    def all(self):
        return [self[alias] for alias in self]

    def close_all(self):
        for alias in self:
            try:
                connection = getattr(self._connections, alias)
            except AttributeError:
                continue
            connection.close()


class ConnectionRouter(object):
    def __init__(self, routers=None):
        """
        If routers is not specified, will default to settings.DATABASE_ROUTERS.
        """
        self._routers = routers

    @cached_property
    def routers(self):
        if self._routers is None:
            self._routers = settings.DATABASE_ROUTERS
        routers = []
        for r in self._routers:
            if isinstance(r, six.string_types):
                router = import_string(r)()
            else:
                router = r
            routers.append(router)
        return routers

    def _router_func(action):
        def _route_db(self, model, **hints):
            chosen_db = None
            for router in self.routers:
                try:
                    method = getattr(router, action)
                except AttributeError:
                    # If the router doesn't have a method, skip to the next one.
                    pass
                else:
                    chosen_db = method(model, **hints)
                    if chosen_db:
                        return chosen_db
            instance = hints.get('instance')
            if instance is not None and instance._state.db:
                return instance._state.db
            return DEFAULT_DB_ALIAS
        return _route_db

    db_for_read = _router_func('db_for_read')
    db_for_write = _router_func('db_for_write')

    def allow_relation(self, obj1, obj2, **hints):
        for router in self.routers:
            try:
                method = router.allow_relation
            except AttributeError:
                # If the router doesn't have a method, skip to the next one.
                pass
            else:
                allow = method(obj1, obj2, **hints)
                if allow is not None:
                    return allow
        return obj1._state.db == obj2._state.db

    def allow_migrate(self, db, app_label, **hints):
        for router in self.routers:
            try:
                method = router.allow_migrate
            except AttributeError:
                # If the router doesn't have a method, skip to the next one.
                continue

            if six.PY3:
                sig = inspect.signature(router.allow_migrate)
                has_deprecated_signature = not any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                )
            else:
                argspec = inspect.getargspec(router.allow_migrate)
                has_deprecated_signature = len(argspec.args) == 3 and not argspec.keywords

            if has_deprecated_signature:
                warnings.warn(
                    "The signature of allow_migrate has changed from "
                    "allow_migrate(self, db, model) to "
                    "allow_migrate(self, db, app_label, model_name=None, **hints). "
                    "Support for the old signature will be removed in Django 1.10.",
                    RemovedInDjango110Warning)
                model = hints.get('model')
                allow = None if model is None else method(db, model)
            else:
                allow = method(db, app_label, **hints)

            if allow is not None:
                return allow
        return True

    def allow_migrate_model(self, db, model):
        return self.allow_migrate(
            db,
            model._meta.app_label,
            model_name=model._meta.model_name,
            model=model,
        )

    def get_migratable_models(self, app_config, db, include_auto_created=False):
        """
        Return app models allowed to be synchronized on provided db.
        """
        models = app_config.get_models(include_auto_created=include_auto_created)
        return [model for model in models if self.allow_migrate_model(db, model)]

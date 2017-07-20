import inspect
from collections import defaultdict

from django.core.exceptions import ImproperlyConfigured
from django.utils import module_loading

BACKENDS = defaultdict(dict)


def add_backend(backend_type, scheme, path):
    if scheme in BACKENDS[backend_type]:
        raise ImproperlyConfigured('Scheme {0} has already been registered as a {1} handler'.format(scheme,
                                                                                                    backend_type))
    BACKENDS[backend_type][scheme] = path


def get_backend(backend_type, scheme):
    if scheme not in BACKENDS[backend_type]:
        raise ImproperlyConfigured('No {0} handler configured for {1}'.format(backend_type, scheme))
    return BACKENDS[backend_type][scheme]


def configure(backend_type, value):
    scheme = value.split(':', 1)[0]

    backend_path = get_backend(backend_type, scheme)
    handler = module_loading.import_string(backend_path + '.base.DatabaseWrapper')

    if not hasattr(handler, 'config_from_url'):
        raise RuntimeError('{0} has no config_from_url method'.format(backend_path))

    if not inspect.ismethod(handler.config_from_url):
        raise RuntimeError('{0} is not a class method'.format(handler.config_from_url))

    return handler.config_from_url(backend_path, scheme, value)


# Convenience functions


def configure_db(value):
    return configure('db', value)


def configure_cache(value):
    return configure('cache', value)


def register_db_backend(scheme, path):
    add_backend('db', scheme, path)


def register_cache_backend(scheme, path):
    add_backend('cache', scheme, path)


register_db_backend('mysql', 'django.db.backends.mysql')
register_db_backend('oracle', 'django.db.backends.oracle')
register_db_backend('postgres', 'django.db.backends.postgresql')
register_db_backend('sqlite', 'django.db.backends.sqlite3')

register_db_backend('mysql+gis', 'django.contrib.gis.db.backends.mysql')
register_db_backend('oracle+gis', 'django.contrib.gis.db.backends.oracle')
register_db_backend('postgis', 'django.contrib.gis.db.backends.postgis')
register_db_backend('spatialite', 'django.contrib.gis.db.backends.spatialite')

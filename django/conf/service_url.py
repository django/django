import inspect
from collections import defaultdict
from urllib import parse

from django.core.exceptions import ImproperlyConfigured
from django.utils import module_loading

BACKENDS = defaultdict(dict)


def parse_url(url):
    """
    A method to parse URLs into components that handles quirks
    with the stdlib urlparse, such as lower-cased hostnames.
    Also parses querystrings into typed components.
    """
    # This method may be called with an already parsed URL
    if isinstance(url, dict):
        return url
    parsed = parse.urlparse(url)
    # parsed.hostname always returns a lower-cased hostname
    # this isn't correct if hostname is a file path, so use '_hostinfo'
    # to get the actual host
    hostname, port = parsed._hostinfo
    query = parse.parse_qs(parsed.query)
    options = {}

    for key, values in query.items():
        value = values[-1]
        if value.isdigit():
            value = int(value)
        elif value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False

        options[key] = value

    path = parsed.path[1:]
    if port:
        port = int(port)

    return {
        'scheme': parsed.scheme,
        'username': parsed.username,
        'password': parsed.password,
        'hostname': hostname,
        'port': port,
        'path': path,
        'options': options
    }


def _register_backend(backend_type, scheme, path):
    if scheme in BACKENDS[backend_type]:
        raise ImproperlyConfigured('Scheme {0} has already been registered as a {1} handler'.format(scheme,
                                                                                                    backend_type))
    BACKENDS[backend_type][scheme] = path


def _get_backend(backend_type, scheme):
    if scheme not in BACKENDS[backend_type]:
        raise ImproperlyConfigured('No {0} handler configured for {1}'.format(backend_type, scheme))
    return BACKENDS[backend_type][scheme]


def _get_config(backend_type, value):
    scheme = value.split(':', 1)[0]

    backend_path = _get_backend(backend_type, scheme)
    handler = module_loading.import_string(backend_path)

    if not hasattr(handler, 'config_from_url'):
        raise TypeError('{0} has no config_from_url method'.format(backend_path))

    if not inspect.ismethod(handler.config_from_url):
        raise TypeError('{0} is not a class method'.format(handler.config_from_url))

    if backend_path.endswith('.base.DatabaseWrapper'):
        backend_path = backend_path.replace('.base.DatabaseWrapper', '')

    return handler.config_from_url(backend_path, scheme, value)


# Convenience functions


def configure_db(value):
    return _get_config('db', value)


def configure_cache(value):
    return _get_config('cache', value)


def register_db_backend(scheme, path):
    if not path.endswith('.base.DatabaseWrapper'):
        path += '.base.DatabaseWrapper'

    _register_backend('db', scheme, path)


def register_cache_backend(scheme, path):
    _register_backend('cache', scheme, path)


register_db_backend('mysql', 'django.db.backends.mysql')
register_db_backend('oracle', 'django.db.backends.oracle')
register_db_backend('postgres', 'django.db.backends.postgresql')
register_db_backend('sqlite', 'django.db.backends.sqlite3')

register_db_backend('mysql+gis', 'django.contrib.gis.db.backends.mysql')
register_db_backend('oracle+gis', 'django.contrib.gis.db.backends.oracle')
register_db_backend('postgis', 'django.contrib.gis.db.backends.postgis')
register_db_backend('spatialite', 'django.contrib.gis.db.backends.spatialite')

register_cache_backend('memory', 'django.core.cache.backends.locmem.LocMemCache')
register_cache_backend('db', 'django.core.cache.backends.db.DatabaseCache')
register_cache_backend('dummy', 'django.core.cache.backends.dummy.DummyCache')
register_cache_backend('memcached', 'django.core.cache.backends.memcached.MemcachedCache')
register_cache_backend('memcached+pylibmccache', 'django.core.cache.backends.memcached.PyLibMCCache')
register_cache_backend('file', 'django.core.cache.backends.filebased.FileBasedCache')

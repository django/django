import os
from urllib import parse

from django.core.exceptions import ImproperlyConfigured

# These constants are used in the parsing code, rather than duplicating the paths
POSTGRES = 'django.db.backends.postgresql_psycopg2'
POSTGIS = 'django.contrib.gis.db.backends.postgis'

MYSQL = 'django.db.backends.mysql'
MYSQLGIS = 'django.contrib.gis.db.backends.mysql'

SQLITE = 'django.db.backends.sqlite3'
SPATALITE = 'django.contrib.gis.db.backends.spatialite'

ORACLE = 'django.db.backends.oracle'
ORACLEGIS = 'django.contrib.gis.db.backends.oracle'

SCHEMES = {
    'postgres': POSTGRES,
    'postgresql': POSTGRES,
    'pgsql': POSTGRES,
    'postgis': POSTGIS,

    'mysql': MYSQL,
    'mysql2': MYSQL,
    'mysqlgis': MYSQLGIS,

    'sqlite': SQLITE,
    'sqlite3': SQLITE,
    'spatialite': SPATALITE,

    'oracle': ORACLE,
    'oraclegis': ORACLEGIS,
}


def parse_url(url, **defaults):
    # Note: I don't like this special case... seems fragile.
    if url == 'sqlite://:memory:':
        # this is a special case, because if we pass this URL into
        # urlparse, urlparse will choke trying to interpret "memory"
        # as a port number
        return {
            'ENGINE': SCHEMES['sqlite'],
            'NAME': ':memory:'
        }

    # urlsplit.scheme doesn't work with schemes that contain underscores.
    # Here we attempt to handle that:
    scheme = None
    maybe_scheme, rest_url = url.split(':', 1)
    if '_' in maybe_scheme:
        scheme = maybe_scheme
        url = rest_url

    parsed = parse.urlsplit(url)

    if scheme is None:
        scheme = parsed.scheme

    hostname = parsed.hostname or ''
    # Handle postgres percent-encoded paths.
    if '%2f' in hostname:
        # parsed.hostname always returns lowercased hosts. We have to use the `netloc` to
        # access the unlowered hostname.
        hostname = parsed.netloc
        if "@" in hostname:
            hostname = hostname.rsplit("@", 1)[1]
        if ":" in hostname:
            hostname = hostname.split(":", 1)[0]

        hostname = hostname.replace('%2f', '/').replace('%2F', '/')

    engine = SCHEMES.get(scheme, scheme)

    name = parsed.path[1:]

    # If we are using sqlite and we have no path, then assume we
    # want an in-memory database (this is the behaviour of sqlalchemy)
    if engine in (SQLITE, SPATALITE) and not name:
        name = ':memory:'

    query = parse.parse_qs(parsed.query)

    options = {}
    for key, values in query.items():
        if parsed.scheme == 'mysql' and key == 'ssl-ca':
            options['ssl'] = {'ca': values[-1]}
            continue

        options[key] = values[-1]

    if 'currentSchema' in options and engine in (POSTGRES, POSTGIS):
        options['options'] = '-c search_path={0}'.format(options.pop('currentSchema'))

    result = {
        'ENGINE': parse.unquote(engine),
        'NAME': parse.unquote(name),
        'USER': parse.unquote(parsed.username or ''),
        'PASSWORD': parse.unquote(parsed.password or ''),
        'HOST': hostname,
        'PORT': parsed.port or '',
    }
    if options:
        result['OPTIONS'] = options

    # Would like to just do **defaults in the expression above, but it's 3.5 syntax only.
    result.update(defaults)

    return result


def parse_from_environment(key='DATABASE_URL', **defaults):
    """
    Convenience function to read an environment variable into a settings dictionary with a single 'default' key.
    """
    if key not in os.environ:
        raise ImproperlyConfigured('Database environment variable {0} not present'.format(key))

    return {
        'default': parse_url(os.environ[key], **defaults)
    }

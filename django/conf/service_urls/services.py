from urllib import parse

from .base import Service


class DbService(Service):
    def config_from_url(self, engine, scheme, url):
        parsed = self.parse_url(url)
        return {
            'ENGINE': engine,
            'NAME': parse.unquote(parsed['path'] or ''),
            'USER': parse.unquote(parsed['username'] or ''),
            'PASSWORD': parse.unquote(parsed['password'] or ''),
            'HOST': parsed['hostname'],
            'PORT': parsed['port'] or '',
            'OPTIONS': parsed['options'],
        }


db = DbService()


@db.register(('sqlite', 'django.db.backends.sqlite3'), ('spatialite', 'django.contrib.gis.db.backends.spatialite'))
def sqlite_config_from_url(backend, engine, scheme, url):
    # These special URLs cannot be parsed correctly.
    if url in ('sqlite://:memory:', 'sqlite://'):
        return {
            'ENGINE': engine,
            'NAME': ':memory:',
        }

    parsed = backend.parse_url(url)
    path = '/' + parsed['path']
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed['hostname']:
        path = '{0}:{1}'.format(parsed['hostname'], path)
        parsed['location'] = parsed['hostname'] = ''
    parsed['path'] = path
    return backend.config_from_url(engine, scheme, parsed)


@db.register(
    ('postgres', 'django.db.backends.postgresql'), ('postgis', 'django.contrib.gis.db.backends.postgis'),
    # dj_database_url compat aliases
    ('postgresql', 'django.db.backends.postgresql'), ('pgsql', 'django.db.backends.postgresql'),
)
def postgresql_config_from_url(backend, engine, scheme, url):
    parsed = backend.parse_url(url)
    host = parsed['hostname'].lower()
    # Handle postgres percent-encoded paths.
    if '%2f' in host or '%3a' in host:
        parsed['hostname'] = parse.unquote(parsed['hostname'])
    config = backend.config_from_url(engine, scheme, parsed)
    if 'currentSchema' in config['OPTIONS']:
        value = config['OPTIONS'].pop('currentSchema')
        config['OPTIONS']['options'] = '-c search_path={0}'.format(value)
    return config


@db.register(('mysql', 'django.db.backends.mysql'), ('mysql+gis', 'django.contrib.gis.db.backends.mysql'))
def mysql_config_from_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    if 'ssl-ca' in config['OPTIONS']:
        value = config['OPTIONS'].pop('ssl-ca')
        config['OPTIONS']['ssl'] = {'ca': value}
    return config


@db.register(('oracle', 'django.db.backends.oracle'), ('oracle+gis', 'django.contrib.gis.db.backends.oracle'))
def oracle_config_from_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    # Oracle requires string ports
    config['PORT'] = str(config['PORT'])
    return config


class CacheService(Service):
    def config_from_url(self, engine, scheme, url, *, multiple_netloc=True):
        parsed = self.parse_url(url, multiple_netloc=multiple_netloc)
        config = {
            'BACKEND': engine,
        }
        if multiple_netloc and parsed['location']:
            config['LOCATION'] = parsed['location']
        else:
            if parsed['hostname']:
                config['LOCATION'] = parsed['hostname']
                if parsed['port']:
                    config['LOCATION'] += ':%s' % parsed['port']
        for key in ('timeout', 'key_prefix', 'version'):
            if key in parsed['options']:
                option = parsed['options'].pop(key)
                config[key.upper()] = option
        config['OPTIONS'] = parsed['options']
        return config


cache = CacheService()


@cache.register(('memory', 'django.core.cache.backends.locmem.LocMemCache'))
def memory_config_from_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@cache.register(('db', 'django.core.cache.backends.db.DatabaseCache'))
def db_config_from_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@cache.register(('dummy', 'django.core.cache.backends.dummy.DummyCache'))
def dummy_config_from_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@cache.register(('memcached', 'django.core.cache.backends.memcached.MemcachedCache'))
def memcached_config_from_url(backend, engine, scheme, url):
    parsed = backend.parse_url(url, multiple_netloc=True)
    config = backend.config_from_url(engine, scheme, parsed, multiple_netloc=True)
    if parsed['path']:
        # We are dealing with a URI like memcached:///socket/path
        config['LOCATION'] = 'unix:/{0}'.format(parsed['path'])
    return config


@cache.register(('memcached+pylibmccache', 'django.core.cache.backends.memcached.PyLibMCCache'))
def pylibmccache_config_from_url(backend, engine, scheme, url):
    parsed = backend.parse_url(url, multiple_netloc=True)
    # We are dealing with a URI like memcached://unix:/abc
    # Set the hostname to be the unix path
    parsed['hostname'] = '/{}'.format(parsed['path'])
    parsed['path'] = None
    return backend.config_from_url(engine, scheme, parsed)


@cache.register(('file', 'django.core.cache.backends.filebased.FileBasedCache'))
def file_config_from_url(backend, engine, scheme, url):
    parsed = backend.parse_url(url)
    config = backend.config_from_url(engine, scheme, parsed)
    path = '/' + parsed['path']
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed['hostname']:
        path = '{0}:{1}'.format(parsed['hostname'], path)
    config['LOCATION'] = path
    return config


class EmailService(Service):
    def config_from_url(self, engine, scheme, url):
        return {
            'ENGINE': engine,
        }


email = EmailService()


@email.register(
    ('smtp', 'django.core.mail.backends.smtp.EmailBackend'),
    ('smtps', 'django.core.mail.backends.smtp.EmailBackend'),  # smtp+tls alias
    ('smtp+tls', 'django.core.mail.backends.smtp.EmailBackend'),
    ('smtp+ssl', 'django.core.mail.backends.smtp.EmailBackend'),
)
def email_smtp_config_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    parsed = backend.parse_url(url)
    return {
        'HOST': parsed['hostname'] or 'localhost',
        'PORT': parsed['port'] or 25,
        'HOST_USER': parsed['username'] or '',
        'HOST_PASSWORD': parsed['password'] or '',
        'USE_TLS': parsed['options'].get('use_tls', scheme in ('smtps', 'smtp+tls')),
        'USE_SSL': parsed['options'].get('use_ssl', scheme == 'smtp+ssl'),
        'SSL_CERTFILE': parsed['options'].get('ssl_certfile', None),
        'SSL_KEYFILE': parsed['options'].get('ssl_keyfile', None),
        'TIMEOUT': parsed['options'].get('timeout', None),
        'USE_LOCALTIME': parsed['options'].get('use_localtime', False),
        **config,
    }


@email.register(('console', 'django.core.mail.backends.console.EmailBackend'))
def email_console_config_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@email.register(('file', 'django.core.mail.backends.filebased.EmailBackend'))
def email_file_config_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    parsed = backend.parse_url(url)
    path = '/' + parsed['path']
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed['hostname']:
        path = '{0}:{1}'.format(parsed['hostname'], path)
    return {
        'FILE_PATH': path,
        **config,
    }


@email.register(('memory', 'django.core.mail.backends.locmem.EmailBackend'))
def email_memory_config_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@email.register(('dummy', 'django.core.mail.backends.dummy.EmailBackend'))
def email_dummy_config_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)

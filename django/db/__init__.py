from django.conf import settings
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionHandler, load_backend
from django.utils.functional import curry

__all__ = ('backend', 'connection', 'connections', 'DatabaseError',
    'IntegrityError', 'DEFAULT_DB_ALIAS')

DEFAULT_DB_ALIAS = 'default'

# For backwards compatibility - Port any old database settings over to
# the new values.
if not settings.DATABASES:
    import warnings
    warnings.warn(
        "settings.DATABASE_* is deprecated; use settings.DATABASES instead.",
        PendingDeprecationWarning
    )

    settings.DATABASES[DEFAULT_DB_ALIAS] = {
        'ENGINE': settings.DATABASE_ENGINE,
        'HOST': settings.DATABASE_HOST,
        'NAME': settings.DATABASE_NAME,
        'OPTIONS': settings.DATABASE_OPTIONS,
        'PASSWORD': settings.DATABASE_PASSWORD,
        'PORT': settings.DATABASE_PORT,
        'USER': settings.DATABASE_USER,
        'TEST_CHARSET': settings.TEST_DATABASE_CHARSET,
        'TEST_COLLATION': settings.TEST_DATABASE_COLLATION,
        'TEST_NAME': settings.TEST_DATABASE_NAME,
    }

if DEFAULT_DB_ALIAS not in settings.DATABASES:
    raise ImproperlyConfigured("You must default a '%s' database" % DEFAULT_DB_ALIAS)

for alias, database in settings.DATABASES.items():
    if database['ENGINE'] in ("postgresql", "postgresql_psycopg2", "sqlite3", "mysql", "oracle"):
        import warnings
        if 'django.contrib.gis' in settings.INSTALLED_APPS:
            warnings.warn(
                "django.contrib.gis is now implemented as a full database backend. "
                "Modify ENGINE in the %s database configuration to select "
                "a backend from 'django.contrib.gis.db.backends'" % alias,
                PendingDeprecationWarning
            )
            if database['ENGINE'] == 'postgresql_psycopg2':
                full_engine = 'django.contrib.gis.db.backends.postgis'
            elif database['ENGINE'] == 'sqlite3':
                full_engine = 'django.contrib.gis.db.backends.spatialite'
            else:
                full_engine = 'django.contrib.gis.db.backends.%s' % database['ENGINE']
        else:
            warnings.warn(
                "Short names for ENGINE in database configurations are deprecated. "
                "Prepend %s.ENGINE with 'django.db.backends.'" % alias,
                PendingDeprecationWarning
            )
            full_engine = "django.db.backends.%s" % database['ENGINE']
        database['ENGINE'] = full_engine

connections = ConnectionHandler(settings.DATABASES)


# `connection`, `DatabaseError` and `IntegrityError` are convenient aliases
# for backend bits.

# DatabaseWrapper.__init__() takes a dictionary, not a settings module, so
# we manually create the dictionary from the settings, passing only the
# settings that the database backends care about. Note that TIME_ZONE is used
# by the PostgreSQL backends.
# we load all these up for backwards compatibility, you should use
# connections['default'] instead.
connection = connections[DEFAULT_DB_ALIAS]
backend = load_backend(connection.settings_dict['ENGINE'])
DatabaseError = backend.DatabaseError
IntegrityError = backend.IntegrityError

# Register an event that closes the database connection
# when a Django request is finished.
def close_connection(**kwargs):
    connection.close()
signals.request_finished.connect(close_connection)

# Register an event that resets connection.queries
# when a Django request is started.
def reset_queries(**kwargs):
    for connection in connections.all():
        connection.queries = []
signals.request_started.connect(reset_queries)

# Register an event that rolls back the connections
# when a Django request has an exception.
def _rollback_on_exception(**kwargs):
    from django.db import transaction
    for conn in connections:
        try:
            transaction.rollback_unless_managed(using=conn)
        except DatabaseError:
            pass
signals.got_request_exception.connect(_rollback_on_exception)

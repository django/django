from django.conf import settings
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionHandler, load_backend
from django.utils.functional import curry

__all__ = ('backend', 'connection', 'connections', 'DatabaseError',
    'IntegrityError', 'DEFAULT_DB_ALIAS')

DEFAULT_DB_ALIAS = 'default'

if not settings.DATABASES or DEFAULT_DB_ALIAS not in settings.DATABASES:
    settings.DATABASES[DEFAULT_DB_ALIAS] = {
        'DATABASE_ENGINE': settings.DATABASE_ENGINE,
        'DATABASE_HOST': settings.DATABASE_HOST,
        'DATABASE_NAME': settings.DATABASE_NAME,
        'DATABASE_OPTIONS': settings.DATABASE_OPTIONS,
        'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
        'DATABASE_PORT': settings.DATABASE_PORT,
        'DATABASE_USER': settings.DATABASE_USER,
        'TIME_ZONE': settings.TIME_ZONE,

        'TEST_DATABASE_CHARSET': settings.TEST_DATABASE_CHARSET,
        'TEST_DATABASE_COLLATION': settings.TEST_DATABASE_COLLATION,
        'TEST_DATABASE_NAME': settings.TEST_DATABASE_NAME,
    }

connections = ConnectionHandler(settings.DATABASES)


# `connection`, `DatabaseError` and `IntegrityError` are convenient aliases
# for backend bits.

# DatabaseWrapper.__init__() takes a dictionary, not a settings module, so
# we manually create the dictionary from the settings, passing only the
# settings that the database backends care about. Note that TIME_ZONE is used
# by the PostgreSQL backends.
# we load all these up for backwards compatibility, you should use
# connections['default'] instead.
connection = connections['default']
backend = load_backend(settings.DATABASE_ENGINE)
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
    connection.queries = []
signals.request_started.connect(reset_queries)

# Register an event that rolls back the connection
# when a Django request has an exception.
def _rollback_on_exception(**kwargs):
    from django.db import transaction
    try:
        transaction.rollback_unless_managed()
    except DatabaseError:
        pass
signals.got_request_exception.connect(_rollback_on_exception)

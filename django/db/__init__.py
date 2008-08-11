import os
from django.conf import settings
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import curry

__all__ = ('backend', 'connection', 'DatabaseError', 'IntegrityError')

if not settings.DATABASE_ENGINE:
    settings.DATABASE_ENGINE = 'dummy'

try:
    # Most of the time, the database backend will be one of the official
    # backends that ships with Django, so look there first.
    _import_path = 'django.db.backends.'
    backend = __import__('%s%s.base' % (_import_path, settings.DATABASE_ENGINE), {}, {}, [''])
except ImportError, e:
    # If the import failed, we might be looking for a database backend
    # distributed external to Django. So we'll try that next.
    try:
        _import_path = ''
        backend = __import__('%s.base' % settings.DATABASE_ENGINE, {}, {}, [''])
    except ImportError, e_user:
        # The database backend wasn't found. Display a helpful error message
        # listing all possible (built-in) database backends.
        backend_dir = os.path.join(__path__[0], 'backends')
        available_backends = [f for f in os.listdir(backend_dir) if not f.startswith('_') and not f.startswith('.') and not f.endswith('.py') and not f.endswith('.pyc')]
        available_backends.sort()
        if settings.DATABASE_ENGINE not in available_backends:
            raise ImproperlyConfigured, "%r isn't an available database backend. Available options are: %s\nError was: %s" % \
                (settings.DATABASE_ENGINE, ", ".join(map(repr, available_backends)), e_user)
        else:
            raise # If there's some other error, this must be an error in Django itself.

# Convenient aliases for backend bits.
connection = backend.DatabaseWrapper(**settings.DATABASE_OPTIONS)
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
    transaction.rollback_unless_managed()
signals.got_request_exception.connect(_rollback_on_exception)

import os
from django.conf import settings
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import curry

__all__ = ('backend', 'connection', 'DatabaseError', 'IntegrityError')

if not settings.DATABASE_ENGINE:
    settings.DATABASE_ENGINE = 'dummy'

def load_backend(backend_name):
    try:
        # Most of the time, the database backend will be one of the official
        # backends that ships with Django, so look there first.
        return __import__('django.db.backends.%s.base' % backend_name, {}, {}, [''])
    except ImportError, e:
        # If the import failed, we might be looking for a database backend
        # distributed external to Django. So we'll try that next.
        try:
            return __import__('%s.base' % backend_name, {}, {}, [''])
        except ImportError, e_user:
            # The database backend wasn't found. Display a helpful error message
            # listing all possible (built-in) database backends.
            backend_dir = os.path.join(__path__[0], 'backends')
            try:
                available_backends = [f for f in os.listdir(backend_dir)
                        if os.path.isdir(os.path.join(backend_dir, f))]
            except EnvironmentError:
                available_backends = []
            available_backends.sort()
            if backend_name not in available_backends:
                error_msg = "%r isn't an available database backend. Available options are: %s\nError was: %s" % \
                    (backend_name, ", ".join(map(repr, available_backends)), e_user)
                raise ImproperlyConfigured(error_msg)
            else:
                raise # If there's some other error, this must be an error in Django itself.

backend = load_backend(settings.DATABASE_ENGINE)

# `connection`, `DatabaseError` and `IntegrityError` are convenient aliases
# for backend bits.

# DatabaseWrapper.__init__() takes a dictionary, not a settings module, so
# we manually create the dictionary from the settings, passing only the
# settings that the database backends care about. Note that TIME_ZONE is used
# by the PostgreSQL backends.
connection = backend.DatabaseWrapper({
    'DATABASE_HOST': settings.DATABASE_HOST,
    'DATABASE_NAME': settings.DATABASE_NAME,
    'DATABASE_OPTIONS': settings.DATABASE_OPTIONS,
    'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
    'DATABASE_PORT': settings.DATABASE_PORT,
    'DATABASE_USER': settings.DATABASE_USER,
    'TIME_ZONE': settings.TIME_ZONE,
})
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

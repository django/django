from django.conf.settings import DATABASE_ENGINE
from django.core import signals
from django.dispatch import dispatcher

__all__ = ('backend', 'connection', 'DatabaseError')

if not DATABASE_ENGINE:
    DATABASE_ENGINE = 'dummy'

try:
    backend = __import__('django.db.backends.%s.base' % DATABASE_ENGINE, '', '', [''])
except ImportError, e:
    # The database backend wasn't found. Display a helpful error message
    # listing all possible database backends.
    from django.core.exceptions import ImproperlyConfigured
    import os
    backend_dir = os.path.join(__path__[0], 'backends')
    available_backends = [f for f in os.listdir(backend_dir) if not f.startswith('_') and not f.startswith('.') and not f.endswith('.py') and not f.endswith('.pyc')]
    available_backends.sort()
    raise ImproperlyConfigured, "Could not load database backend: %s. Is your DATABASE_ENGINE setting (currently, %r) spelled correctly? Available options are: %s" % \
        (e, DATABASE_ENGINE, ", ".join(map(repr, available_backends)))

get_introspection_module = lambda: __import__('django.db.backends.%s.introspection' % DATABASE_ENGINE, '', '', [''])
get_creation_module = lambda: __import__('django.db.backends.%s.creation' % DATABASE_ENGINE, '', '', [''])

connection = backend.DatabaseWrapper()
DatabaseError = backend.DatabaseError

# Register an event that closes the database connection
# when a Django request is finished.
dispatcher.connect(lambda: connection.close(), signal=signals.request_finished)

# Register an event that resets connection.queries
# when a Django request is started.
def reset_queries():
    connection.queries = []
dispatcher.connect(reset_queries, signal=signals.request_started)

# Register an event that rolls back the connection
# when a Django request has an exception.
dispatcher.connect(lambda: connection.rollback(), signal=signals.got_request_exception)

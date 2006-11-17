from django.conf import settings
from django.core import signals
from django.dispatch import dispatcher

__all__ = ('backend', 'connection', 'DatabaseError')

if not settings.DATABASE_ENGINE:
    settings.DATABASE_ENGINE = 'dummy'

try:
    backend = __import__('django.db.backends.%s.base' % settings.DATABASE_ENGINE, {}, {}, [''])
except ImportError, e:
    # The database backend wasn't found. Display a helpful error message
    # listing all possible database backends.
    from django.core.exceptions import ImproperlyConfigured
    import os
    backend_dir = os.path.join(__path__[0], 'backends')
    available_backends = [f for f in os.listdir(backend_dir) if not f.startswith('_') and not f.startswith('.') and not f.endswith('.py') and not f.endswith('.pyc')]
    available_backends.sort()
    if settings.DATABASE_ENGINE not in available_backends:
        raise ImproperlyConfigured, "%r isn't an available database backend. Available options are: %s" % \
            (settings.DATABASE_ENGINE, ", ".join(map(repr, available_backends)))
    else:
        raise # If there's some other error, this must be an error in Django itself.

def backend_module_accessor(module_name):
    def accessor():
        full_name = 'django.db.backends.%s.%s' % (settings.DATABASE_ENGINE, module_name)
        return __import__(full_name, {}, {}, [''])
    return accessor

get_introspection_module = backend_module_accessor("introspection")
get_creation_module = backend_module_accessor("creation")
get_query_module = backend_module_accessor("query")
get_client_module = backend_module_accessor("client")
runshell = lambda: get_client_module().runshell()

connection = backend.DatabaseWrapper(**settings.DATABASE_OPTIONS)

DatabaseError = backend.DatabaseError

# Register an event that closes the database connection
# when a Django request is finished.
dispatcher.connect(connection.close, signal=signals.request_finished)

# Register an event that resets connection.queries
# when a Django request is started.
def reset_queries():
    connection.queries = []
dispatcher.connect(reset_queries, signal=signals.request_started)

# Register an event that rolls back the connection
# when a Django request has an exception.
def _rollback_on_exception():
    from django.db import transaction
    transaction.rollback_unless_managed()
dispatcher.connect(_rollback_on_exception, signal=signals.got_request_exception)

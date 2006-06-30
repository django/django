from django.conf import settings, UserSettingsHolder
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import dispatcher

__all__ = ('backend', 'connection', 'DatabaseError')

if not settings.DATABASE_ENGINE:
    settings.DATABASE_ENGINE = 'dummy'

def connect(settings):
    """Connect to the database specified in settings. Returns a
    ConnectionInfo on succes, raises ImproperlyConfigured if the
    settings don't specify a valid database connection.
    """
    try:
        backend = __import__('django.db.backends.%s.base' % settings.DATABASE_ENGINE, '', '', [''])
    except ImportError, e:
        # The database backend wasn't found. Display a helpful error message
        # listing all possible database backends.
        import os
        backend_dir = os.path.join(__path__[0], 'backends')
        available_backends = [f for f in os.listdir(backend_dir) if not f.startswith('_') and not f.startswith('.') and not f.endswith('.py') and not f.endswith('.pyc')]
        available_backends.sort()
        if settings.DATABASE_ENGINE not in available_backends:
            raise ImproperlyConfigured, "%r isn't an available database backend. vailable options are: %s" % \
                (settings.DATABASE_ENGINE, ", ".join(map(repr, available_backends)))
        else:
            raise # If there's some other error, this must be an error in Django itself.

    info = ConnectionInfo(backend, settings)

    # Register an event that closes the database connection
    # when a Django request is finished.
    dispatcher.connect(info.close, signal=signals.request_finished)
    
    # Register an event that resets connection.queries
    # when a Django request is started.
    dispatcher.connect(info.reset_queries, signal=signals.request_started)

    return info

    
class ConnectionInfo(object):
    """Encapsulates all information about a connection and the backend
    to which it belongs. Provides methods for loading backend
    creation, introspection, and shell modules, closing the
    connection, and resetting the connection's query log.
    """
    def __init__(self, backend, settings): 
        self.backend = backend
        self.settings = settings
        self.connection = backend.DatabaseWrapper(settings)
        self.DatabaseError = backend.DatabaseError

    def __repr__(self):
        return "Connection: %r (ENGINE=%s NAME=%s)" \
               % (self.connection,
                  self.settings.DATABASE_ENGINE,
                  self.settings.DATABASE_NAME)

    def close(self):
        """Close connection"""
        self.connection.close()

    def get_introspection_module(self):
        return __import__('django.db.backends.%s.introspection' % 
                          self.settings.DATABASE_ENGINE, '', '', [''])

    def get_creation_module(self):
        return __import__('django.db.backends.%s.creation' % 
                          self.settings.DATABASE_ENGINE, '', '', [''])

    def runshell(self):
        __import__('django.db.backends.%s.client' %
                   self.settings.DATABASE_ENGINE, '', '', ['']).runshell()
        
    def reset_queries(self):
        """Reset log of queries executed by connection"""
        self.connection.queries = []


class LazyConnectionManager(object):
    """Manages named connections lazily, instantiating them as
    they are requested.
    """
    def __init__(self):
        self._connections = {}

    def __iter__(self):
        return self._connections.keys()

    def __getattr__(self, attr):
        # use __dict__ to avoid getattr() loop
        return getattr(self.__dict__['_connections'], attr)

    def __getitem__(self, k):
        try:
            return self.__dict__['_connections'][k]
        except KeyError:
            return self.connect(k)

    def __setitem__(self, k, v):
        self.__dict__['_connections'][k] = v
            
    def connect(self, name):
        """Return the connection with this name in
        settings.DATABASES. Creates the connection if it doesn't yet
        exist. Reconnects if it does.
        """
        if name in self._connections:
            self._connections[name].close()
        try:
            info = settings.DATABASES[name]
        except KeyError:
            raise ImproperlyConfigured, \
                  "No database connection '%s' has been configured" % name
        except AttributeError:
            raise ImproperlyConfigured, \
                  "No DATABASES in settings."

        # In settings it's a dict, but connect() needs an object
        # pass global settings so that the default connection settings
        # can be defaults for the named connections
        database = UserSettingsHolder(settings)
        for k, v in info.items():
            setattr(database, k, v)
        self._connections[name] = connect(database)
        return self._connections[name]


# Backwards compatibility: establish the default connection and set the
# default connection properties at module level
connection_info = connect(settings)
(connection, DatabaseError, backend, get_introspection_module, 
 get_creation_module, runshell) = (connection_info.connection,
                                   connection_info.DatabaseError,
                                   connection_info.backend,
                                   connection_info.get_introspection_module, 
                                   connection_info.get_creation_module,
                                   connection_info.runshell)

# Create a manager for named connections
connections = LazyConnectionManager()

# Register an event that rolls back all connections
# when a Django request has an exception.
def _rollback_on_exception():
    from django.db import transaction
    transaction.rollback_unless_managed()
dispatcher.connect(_rollback_on_exception,
                   signal=signals.got_request_exception)



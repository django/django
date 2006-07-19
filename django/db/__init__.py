from django.conf import settings, UserSettingsHolder
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import dispatcher

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

__all__ = ('backend', 'connection', 'DatabaseError')

# singleton to represent the default connection in connections
_default = object()

if not settings.DATABASE_ENGINE:
    settings.DATABASE_ENGINE = 'dummy'

def connect(settings):
    """Connect to the database specified in settings. Returns a
    ConnectionInfo on succes, raises ImproperlyConfigured if the
    settings don't specify a valid database connection.
    """
    info = ConnectionInfo(settings)

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
    def __init__(self, settings=None):
        if settings is None:
            from django.conf import settings
        self.settings = settings
        self.backend = self.load_backend()
        self.connection = self.backend.DatabaseWrapper(settings)
        self.DatabaseError = self.backend.DatabaseError

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

    def load_backend(self):
        try:
            backend = __import__('django.db.backends.%s.base' %
                                 self.settings.DATABASE_ENGINE, '', '', [''])
        except ImportError, e:
            # The database backend wasn't found. Display a helpful error
            # message listing all possible database backends.
            import os
            backend_dir = os.path.join(__path__[0], 'backends')
            available_backends = [f for f in os.listdir(backend_dir)
                                  if not f.startswith('_')  \
                                  and not f.startswith('.') \
                                  and not f.endswith('.py') \
                                  and not f.endswith('.pyc')]
            available_backends.sort()
            if settings.DATABASE_ENGINE not in available_backends:
                raise ImproperlyConfigured, \
                      "%r isn't an available database backend. "\
                      "Available options are: %s" % \
                      (settings.DATABASE_ENGINE,
                       ", ".join(map(repr, available_backends)))
            else:
                # If there's some other error, this must be an error
                # in Django itself.
                raise
        return backend

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
        self.local = local()
        self.local.connections = {}

    def __iter__(self):
        return self.local.connections.keys()

    def __getattr__(self, attr):
        return getattr(self.local.connections, attr)

    def __getitem__(self, k):
        try:
            return self.local.connections[k]
        except KeyError:
            return self.connect(k)

    def __setitem__(self, k, v):
        self.local.connections[k] = v
            
    def connect(self, name):
        """Return the connection with this name in
        settings.OTHER_DATABASES. Creates the connection if it doesn't yet
        exist. Reconnects if it does. If the name requested is the default
        connection (a singleton defined in django.db), then the default
        connection is returned.        
        """
        cnx = self.local.connections
        if name in cnx:
            cnx[name].close()
        if name is _default:
            # get the default connection from connection_info
            if connection_info.local.db is None:
                connection_info.init_connection()
            cnx[name] = connection_info.local.db
            return cnx[name]
        try:
            info = settings.OTHER_DATABASES[name]
        except KeyError:
            raise ImproperlyConfigured, \
                  "No database connection '%s' has been configured" % name
        except AttributeError:
            raise ImproperlyConfigured, \
                  "No OTHER_DATABASES in settings."

        # In settings it's a dict, but connect() needs an object:
        # pass global settings so that the default connection settings
        # can be defaults for the named connections.
        database = UserSettingsHolder(settings)
        for k, v in info.items():
            setattr(database, k, v)
        cnx[name] = connect(database)
        return cnx[name]

    def reset(self):
        self.local.connections = {}


class _proxy:
    """A lazy-initializing proxy. The proxied object is not
    initialized until the first attempt to access it.
    """
    
    def __init__(self, init_obj):
        self.__dict__['_obj'] = None
        self.__dict__['_init_obj'] = init_obj

    def __getattr__(self, attr):
        if self.__dict__['_obj'] is None:
            self.__dict__['_obj'] = self.__dict__['_init_obj']()
        return getattr(self.__dict__['_obj'], attr)

    def __setattr__(self, attr, val):
        if self.__dict__['_obj'] is None:
            self.__dict__['_obj'] = self.__dict__['_init_obj']()
        setattr(self.__dict__['_obj'], attr, val)


class DefaultConnectionInfoProxy(object):
    """Holder for proxy objects that will connect to the current
    default connection when used. Mimics the interface of a ConnectionInfo.
    """
    def __init__(self):
        self.local = local()
        self.local.db = None
        self.connection = _proxy(self.get_connection)
        self.DatabaseError = _proxy(self.get_database_error)
        self.backend = _proxy(self.get_backend)
        self.get_introspection_module = _proxy(self.get_introspection_module)
        self.get_creation_module = _proxy(self.get_creation_module)
        self.runshell = _proxy(self.get_runshell)

    def init_connection(self):
        from django.conf import settings
        self.local.db = connect(settings)

    def get_backend(self):
        if self.local.db is None:
            self.init_connection()
        return self.local.db.backend
        
    def get_connection(self):
        if self.local.db is None:
            self.init_connection()
        return self.local.db.connection

    def get_database_error(self):
        if self.local.db is None:
            self.init_connection()
        return self.local.db.DatabaseError

    def get_introspection_module(self):
        if self.local.db is None:
            self.init_connection()
        return self.local.db.get_introspection_module
    
    def get_creation_module(self):
        if self.local.db is None:
            self.init_connection()
        return self.local.db.get_creation_module
    
    def get_runshell(self):
        if self.local.db is None:
            self.init_connection()
        return self.local.db.runshell
    
    def close(self):
        self.local.db = None
    

def model_connection_name(klass):
    """Get the connection name that a model is configured to use, with the
    given settings.
    """
    app = klass._meta.app_label
    model = klass.__name__
    app_model = "%s.%s" % (app, model)

    # Quick exit if no OTHER_DATABASES defined
    if (not hasattr(settings, 'OTHER_DATABASES')
        or not settings.OTHER_DATABASES):
        return _default
    # Look in MODELS for the best match: app_label.Model. If that isn't
    # found, take just app_label. If nothing is found, use the default
    maybe = None
    for name, db_def in settings.OTHER_DATABASES.items():
        if not 'MODELS' in db_def:
            continue
        mods = db_def['MODELS']
        # Can't get a better match than this
        if app_model in mods:
            return name
        elif app in mods:
            if maybe is not None:
                raise ImproperlyConfigured, \
                    "App %s appears in more than one OTHER_DATABASES " \
                    "setting (%s and %s)" % (maybe, name)
            maybe = name
    if maybe:
        return maybe
    # No named connection for this model; use the default
    return _default

class ConnectionInfoDescriptor(object):
    """Descriptor used to access database connection information from a
    manager or other connection holder. Keeps a thread-local cache of
    connections per instance, and always returns the same connection for an
    instance in particular thread during a particular request.

    Any object that includes an attribute ``model`` that holds a model class
    can use this descriptor to manage connections.
    """
    
    def __init__(self):
        self.cnx = local()
        self.cnx.cache = {}
        
    def __get__(self, instance, type=None):
        if instance is None:
            raise AttributeError, \
                "ConnectionInfo is accessible only through an instance"
        instance_connection = self.cnx.cache.get(instance, None)
        if instance_connection is None:
            instance_connection = self.get_connection(instance)
            def reset():
                self.reset(instance)
            dispatcher.connect(reset, signal=signals.request_finished)
            self.cnx.cache[instance] = instance_connection
        return instance_connection

    def __set__(self, instance, value):
        self.cnx.cache[instance] = instance_connection

    def __delete__(self, instance):
        self.reset(instance)

    def get_connection(self, instance):
        return connections[model_connection_name(instance.model)]
            
    def reset(self, instance):
        self.cnx.cache[instance] = None


        
# Backwards compatibility: establish the default connection and set the
# default connection properties at module level
connection_info = DefaultConnectionInfoProxy()
(connection, DatabaseError, backend, get_introspection_module, 
 get_creation_module, runshell) = (connection_info.connection,
                                   connection_info.DatabaseError,
                                   connection_info.backend,
                                   connection_info.get_introspection_module,
                                   connection_info.get_creation_module,
                                   connection_info.runshell)

# Create a manager for named connections
connections = LazyConnectionManager()

# Reset connections on request finish, to make sure each request can
# load the correct connections for its settings
dispatcher.connect(connections.reset, signal=signals.request_finished)

# Clear the default connection on request finish also
dispatcher.connect(connection_info.close, signal=signals.request_finished)

# Register an event that rolls back all connections
# when a Django request has an exception.
def _rollback_on_exception():
    from django.db import transaction
    transaction.rollback_unless_managed()
dispatcher.connect(_rollback_on_exception,
                   signal=signals.got_request_exception)



from django import conf
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

# storage for local default connection
_local = local()


if not conf.settings.DATABASE_ENGINE:
    conf.settings.DATABASE_ENGINE = 'dummy'


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
            settings = conf.settings
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
            if self.settings.DATABASE_ENGINE not in available_backends:
                raise ImproperlyConfigured, \
                      "%r isn't an available database backend. "\
                      "Available options are: %s" % \
                      (self.settings.DATABASE_ENGINE,
                       ", ".join(map(repr, available_backends)))
            else:
                # If there's some other error, this must be an error
                # in Django itself.
                raise
        return backend

    def runshell(self):
        __import__('django.db.backends.%s.client' %
                   self.settings.DATABASE_ENGINE, '', '', ['']
                   ).runshell(self.settings)
        
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
        except (AttributeError, KeyError):
            return self.connect(k)

    def __setitem__(self, k, v):
        try:
            self.local.connections[k] = v
        except AttributeError:
            # First access in thread
            self.local.connections = {k: v}
            
    def connect(self, name):
        """Return the connection with this name in
        settings.OTHER_DATABASES. Creates the connection if it doesn't yet
        exist. Reconnects if it does. If the name requested is the default
        connection (a singleton defined in django.db), then the default
        connection is returned.        
        """
        settings = conf.settings
        try:
            cnx = self.local.connections
        except AttributeError:
            cnx = self.local.connections = {}
            
        if name in cnx:
            cnx[name].close()
        if name is _default:
            cnx[name] = connect(conf.settings)
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
        database = conf.UserSettingsHolder(settings)
        for k, v in info.items():
            setattr(database, k, v)
        cnx[name] = connect(database)
        return cnx[name]

    def reset(self):
        self.local.connections = {}


def model_connection_name(klass):
    """Get the connection name that a model is configured to use, with the
    current settings.
    """
    settings = conf.settings
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
        self.local = local()
        self.local.cnx = {}
        dispatcher.connect(self.reset, signal=signals.request_finished)
        
    def __get__(self, instance, type=None):
        if instance is None:
            raise AttributeError, \
                "ConnectionInfo is accessible only through an instance"
        try:
            instance_connection = self.local.cnx.get(instance, None)
        except AttributeError:
            # First access in this thread
            self.local.cnx = {}
            instance_connection = None
        if instance_connection is None:
            instance_connection = self.get_connection(instance)
            self.local.cnx[instance] = instance_connection
        return instance_connection

    def __set__(self, instance, value):
        try:
            self.local.cnx[instance] = instance_connection
        except AttributeError:
            # First access in thread
            self.local.cnx = {instance: instance_connection}

    def __delete__(self, instance):
        try:
            del self.local.cnx[instance]
        except (AttributeError, KeyError):
            # Not stored, no need to reset
            pass

    def get_connection(self, instance):
        return connections[model_connection_name(instance.model)]
            
    def reset(self):
        self.local.cnx = {}


class LocalizingProxy:
    """A lazy-initializing proxy. The proxied object is not
    initialized until the first attempt to access it. This is used to
    attach module-level properties to local storage.
    """
    def __init__(self, name, storage, func, *arg, **kw):
        print name, storage, func, arg
        self.__name = name
        self.__storage = storage
        self.__func = func
        self.__arg = arg
        self.__kw = kw
        
    def __getattr__(self, attr):
        if attr.startswith('_LocalizingProxy'):
            return self.__dict__[attr]
        try:
            return getattr(getattr(self.__storage, self.__name), attr)
        except AttributeError:
            setattr(self.__storage, self.__name, self.__func(*self.__arg,
                                                             **self.__kw))
            return getattr(getattr(self.__storage, self.__name), attr)

    def __setattr__(self, attr, val):
        if attr.startswith('_LocalizingProxy'):
            self.__dict__[attr] = val
            return
        try:
            print self.__storage, self.__name
            stor = getattr(self.__storage, self.__name)            
        except AttributeError:
            stor =  self.__func(*self.__arg)
            setattr(self.__storage, self.__name, stor)
        setattr(stor, attr, val)
    

# Create a manager for named connections
connections = LazyConnectionManager()

# Backwards compatibility: establish the default connection and set the
# default connection properties at module level, using the lazy proxy so that
# each thread may have a different default connection, if so configured
connection_info = LocalizingProxy('connection_info', _local,
                                  lambda: connections[_default])
connection = LocalizingProxy('connection', _local,
                             lambda: connections[_default].connection)
backend = LocalizingProxy('backend', _local,
                          lambda: connections[_default].backend)
DatabaseError = LocalizingProxy('DatabaseError', _local,
                                lambda: connections[_default].DatabaseError)
get_introspection_module = LocalizingProxy(
    'get_introspection_module', _local,
    lambda: connections[_default].get_introspection_module)
get_creation_module = LocalizingProxy(
    'get_creation_module', _local,
    lambda: connections[_default].get_creation_module)
runshell = LocalizingProxy('runshell', _local,
                           lambda: connections[_default].runshell)


# Reset connections on request finish, to make sure each request can
# load the correct connections for its settings
dispatcher.connect(connections.reset, signal=signals.request_finished)


# Register an event that rolls back all connections
# when a Django request has an exception.
def _rollback_on_exception():
    from django.db import transaction
    transaction.rollback_unless_managed()
dispatcher.connect(_rollback_on_exception,
                   signal=signals.got_request_exception)



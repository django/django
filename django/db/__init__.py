from django.conf.settings import DATABASE_ENGINE

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

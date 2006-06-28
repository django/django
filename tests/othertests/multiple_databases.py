import copy
import os
import sys
import tempfile
from django.conf import settings
from django import db
from runtests import doctest, DjangoDoctestRunner, error_list

# database files
fh, db_a = tempfile.mkstemp()
os.close(fh)
fh, db_b = tempfile.mkstemp()
os.close(fh)

# patches
tmp_settings = None
tmp_connections = None

# tests
test = r"""
XXX. Using multiple database connections

Django normally uses only a single database connection. However, support is
available for connecting to any number of different, named databases.

Named connections are defined in your settings module. Create a
`DATABASES` variable that is a dict, mapping connection names to their
particulars. The particulars are defined in a dict with the same keys
as the variable names as are used to define the default connection.

.. note::

    Please note that this uses the sqlite3 backend and writes temporary
    database files to disk. This test will fail unless sqlite3 is
    installed and your temp directory is writable.

    >>> from django.conf import settings
    >>> settings.DATABASES = { 
    ...     'a': { 'DATABASE_ENGINE': 'sqlite3',
    ...            'DATABASE_NAME': db_a
    ...     },
    ...     'b': { 'DATABASE_ENGINE': 'sqlite3',
    ...            'DATABASE_NAME': db_b
    ...     }}

Connections are established lazily, when requested by name. When
accessed, `connections[database]` holds a `ConnectionInfo` instance,
with the attributes: `DatabaseError`, `backend`,
`get_introspection_module`, `get_creation_module`, and
`runshell`. Access connections through the `connections` property of
the `django.db` module:

    >>> from django.db import connections
    >>> connections['a'].settings.DATABASE_NAME == db_a
    True
    >>> connections['b'].settings.DATABASE_NAME == db_b
    True
    
Invalid connection names raise ImproperlyConfigured:

    >>> connections['bad']
    Traceback (most recent call last):
        ...
    ImproperlyConfigured: No database connection 'bad' has been configured
"""

def cleanup():
    if os.path.exists(db_a):
        os.unlink(db_a)
    if os.path.exists(db_b):
        os.unlink(db_b)        

def setup():
    global tmp_settings, tmp_connections
    try:
        tmp_connections = db.connections
        db.connections = db.LazyConnectionManager()
        tmp_settings = copy.copy(settings.DATABASES)
    except AttributeError:
        pass
    
def teardown():
    try:
        db.connections = tmp_connections
        settings.DATABASES = tmp_settings
    except AttributeError:
        pass
    cleanup()

def run_tests(verbosity_level):
    setup()
    try:
        main(verbosity_level)
    finally:
        teardown()

def main(verbosity_level):
    mod = sys.modules[__name__]
    p = doctest.DocTestParser()
    dtest = p.get_doctest(mod.test, mod.__dict__, __name__, None, None)
    runner = DjangoDoctestRunner(verbosity_level=verbosity_level,
                                 verbose=False)
    runner.run(dtest, clear_globs=True, out=sys.stdout.write)
    if error_list:
        out = []
        for d in error_list:
            out.extend([d['title'], "=" * len(d['title']),
                        d['description']])

        raise Exception, "%s multiple_databases test%s failed:\n\n %s" \
              % (len(error_list),
                  len(error_list) != 1 and 's' or '',
                 '\n'.join(out))
            
if __name__ == '__main__':
    run_tests(1)

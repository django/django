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

    >>> from django.db import connection, connections
    >>> connections['a'].settings.DATABASE_NAME == db_a
    True
    >>> connections['b'].settings.DATABASE_NAME == db_b
    True
    
Invalid connection names raise ImproperlyConfigured:

    >>> connections['bad']
    Traceback (most recent call last):
        ...
    ImproperlyConfigured: No database connection 'bad' has been configured

Models can define which connection to use, by name. To use a named
connection, set the `db_connection` property in the model's Meta class
to the name of the connection. The name used must be a key in
settings.DATABASES, of course.

    >>> from django.db import models
    >>> class Artist(models.Model):
    ...     name = models.CharField(maxlength=100)
    ...     alive = models.BooleanField(default=True)
    ...     
    ...     def __str__(self):
    ...         return self.name
    ...    
    ...     class Meta:
    ...         app_label = 'mdb'
    ...         db_connection = 'a'
    ...
    >>> class Widget(models.Model):
    ...     code = models.CharField(maxlength=10, unique=True)
    ...     weight = models.IntegerField()
    ... 
    ...     def __str__(self):
    ...         return self.code
    ... 
    ...     class Meta:
    ...         app_label = 'mdb'
    ...         db_connection = 'b'
    
But they don't have to. Multiple database support is entirely optional
and has no impact on your application if you don't use it.

    >>> class Vehicle(models.Model):
    ...     make = models.CharField(maxlength=20)
    ...     model = models.CharField(maxlength=20)
    ...     year = models.IntegerField()
    ... 
    ...     def __str__(self):
    ...         return "%d %s %s" % (self.year, self.make, self.model)
    ...     
    ...     class Meta:
    ...         app_label = 'mdb'

    >>> Artist._meta.connection.settings.DATABASE_NAME == \
    ...     connections['a'].connection.settings.DATABASE_NAME
    True
    >>> Widget._meta.connection.settings.DATABASE_NAME == \
    ...     connections['b'].connection.settings.DATABASE_NAME
    True
    >>> Vehicle._meta.connection.settings.DATABASE_NAME == \
    ...     connection.settings.DATABASE_NAME
    True
    >>> Artist._meta.connection.settings.DATABASE_NAME == \
    ...     Widget._meta.connection.settings.DATABASE_NAME
    False
    >>> Artist._meta.connection.settings.DATABASE_NAME == \
    ...     Vehicle._meta.connection.settings.DATABASE_NAME
    False
    
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

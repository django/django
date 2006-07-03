"""
XXX. Using multiple database connections

Django normally uses only a single database connection. However,
support is available for using any number of different, named
connections. Multiple database support is entirely optional and has
no impact on your application if you don't use it.

Named connections are defined in your settings module. Create a
`DATABASES` variable that is a dict, mapping connection names to their
particulars. The particulars are defined in a dict with the same keys
as the variable names as are used to define the default connection.

Access to named connections is through `django.db.connections`, which
behaves like a dict: you access connections by name. Connections are
established lazily, when accessed.  `django.db.connections[database]`
holds a `ConnectionInfo` instance, with the attributes:
`DatabaseError`, `backend`, `get_introspection_module`,
`get_creation_module`, and `runshell`.

Models can define which connection to use, by name. To use a named
connection, set the `db_connection` property in the model's Meta class
to the name of the connection. The name used must be a key in
settings.DATABASES, of course.

To access a model's connection, use `model._meta.connection`. To find
the backend or other connection metadata, use
`model._meta.connection_info`.
"""

from django.db import models

class Artist(models.Model):
    name = models.CharField(maxlength=100)
    alive = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
   
    class Meta:
        db_connection = 'django_test_db_a'

class Widget(models.Model):
    code = models.CharField(maxlength=10, unique=True)
    weight = models.IntegerField()

    def __str__(self):
        return self.code

    class Meta:
        db_connection = 'django_test_db_b'

class Vehicle(models.Model):
    make = models.CharField(maxlength=20)
    model = models.CharField(maxlength=20)
    year = models.IntegerField()

    def __str__(self):
        return "%d %s %s" % (self.year, self.make, self.model)


API_TESTS = """

# See what connections are defined. django.db.connections acts like a dict.
>>> from django.db import connection, connections
>>> from django.conf import settings
>>> connections.keys()
['django_test_db_a', 'django_test_db_b']

# Each connection references its settings
>>> connections['django_test_db_a'].settings.DATABASE_NAME == settings.DATABASES['django_test_db_a']['DATABASE_NAME']
True
>>> connections['django_test_db_b'].settings.DATABASE_NAME == settings.DATABASES['django_test_db_b']['DATABASE_NAME']
True
>>> connections['django_test_db_b'].settings.DATABASE_NAME == settings.DATABASES['django_test_db_a']['DATABASE_NAME']
False
    
# Invalid connection names raise ImproperlyConfigured
>>> connections['bad']
Traceback (most recent call last):
 ...
ImproperlyConfigured: No database connection 'bad' has been configured

# Models can access their connections through their _meta properties
>>> Artist._meta.connection.settings == connections['django_test_db_a'].settings
True
>>> Widget._meta.connection.settings == connections['django_test_db_b'].settings
True
>>> Vehicle._meta.connection.settings == connection.settings
True
>>> Artist._meta.connection.settings == Widget._meta.connection.settings
False
>>> Artist._meta.connection.settings == Vehicle._meta.connection.settings
False

# Managers use their models' connections

>>> a = Artist(name="Paul Klee", alive=False)
>>> a.save()
>>> w = Widget(code='100x2r', weight=1000)
>>> w.save()
>>> v = Vehicle(make='Chevy', model='Camaro', year='1966')
>>> v.save()
>>> artists = Artist.objects.all()
>>> list(artists)
[<Artist: Paul Klee>]
>>> artists[0]._meta.connection.settings == connections['django_test_db_a'].settings
True
"""

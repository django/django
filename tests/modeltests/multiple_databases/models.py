"""
XXX. Using multiple database connections

Django normally uses only a single database connection. However,
support is available for using any number of different, named
connections. Multiple database support is entirely optional and has
no impact on your application if you don't use it.

Named connections are defined in your settings module. Create a
`OTHER_DATABASES` variable that is a dict, mapping connection names to their
particulars. The particulars are defined in a dict with the same keys
as the variable names as are used to define the default connection, with one
addition: MODELS.

The MODELS item in an OTHER_DATABASES entry is a list of the apps and models
that will use that connection. 

Access to named connections is through `django.db.connections`, which
behaves like a dict: you access connections by name. Connections are
established lazily, when accessed.  `django.db.connections[database]`
holds a `ConnectionInfo` instance, with the attributes:
`DatabaseError`, `backend`, `get_introspection_module`,
`get_creation_module`, and `runshell`.

To access a model's connection, use its manager. The connection is available
at `model._default_manager.db.connection`. To find the backend or other
connection metadata, use `model._meta.db` to access the full ConnectionInfo
with connection metadata.
"""

from django.db import models

class Artist(models.Model):
    name = models.CharField(maxlength=100)
    alive = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

    
class Opus(models.Model):
    artist = models.ForeignKey(Artist)
    name = models.CharField(maxlength=100)
    year = models.IntegerField()
    
    def __str__(self):
        return "%s (%s)" % (self.name, self.year)


class Widget(models.Model):
    code = models.CharField(maxlength=10, unique=True)
    weight = models.IntegerField()

    def __str__(self):
        return self.code


class DooHickey(models.Model):
    name = models.CharField(maxlength=50)
    widgets = models.ManyToManyField(Widget, related_name='doohickeys')
    
    def __str__(self):
        return self.name


class Vehicle(models.Model):
    make = models.CharField(maxlength=20)
    model = models.CharField(maxlength=20)
    year = models.IntegerField()

    def __str__(self):
        return "%d %s %s" % (self.year, self.make, self.model)


__test__ = {'API_TESTS': """

# See what connections are defined. django.db.connections acts like a dict.
>>> from django.db import connection, connections, _default, model_connection_name
>>> from django.conf import settings

# Connections are referenced by name
>>> connections['_a']
Connection: ...
>>> connections['_b']
Connection: ...

# Let's see what connections are available. The default connection is always
# included in connections as well, and may be accessed as connections[_default].

>>> connection_names = connections.keys()
>>> connection_names.sort()
>>> connection_names
[<default>, '_a', '_b']
    
# Invalid connection names raise ImproperlyConfigured

>>> connections['bad']
Traceback (most recent call last):
 ...
ImproperlyConfigured: No database connection 'bad' has been configured

# The model_connection_name() function will tell you the name of the
# connection that a model is configured to use.

>>> model_connection_name(Artist)
'_a'
>>> model_connection_name(Widget)
'_b'
>>> model_connection_name(Vehicle) is _default
True
>>> a = Artist(name="Paul Klee", alive=False)
>>> a.save()
>>> w = Widget(code='100x2r', weight=1000)
>>> w.save()
>>> v = Vehicle(make='Chevy', model='Camaro', year='1966')
>>> v.save()
>>> artists = Artist.objects.all()
>>> list(artists)
[<Artist: Paul Klee>]

# Models can access their connections through the db property of their
# default manager.

>>> paul = _[0]
>>> Artist.objects.db
Connection: ... (ENGINE=... NAME=...)
>>> paul._default_manager.db
Connection: ... (ENGINE=... NAME=...)

# When transactions are not managed, model save will commit only
# for the model's connection.

>>> from django.db import transaction
>>> transaction.enter_transaction_management()
>>> transaction.managed(False)
>>> a = Artist(name="Joan Miro", alive=False)
>>> w = Widget(code="99rbln", weight=1)
>>> a.save()

# Only connection '_a' is committed, so if we rollback
# all connections we'll forget the new Widget.

>>> transaction.rollback()
>>> list(Artist.objects.all())
[<Artist: Paul Klee>, <Artist: Joan Miro>]
>>> list(Widget.objects.all())
[<Widget: 100x2r>]

# Managed transaction state applies across all connections.

>>> transaction.managed(True)

# When managed, just as when using a single connection, updates are
# not committed until a commit is issued.

>>> a = Artist(name="Pablo Picasso", alive=False)
>>> a.save()
>>> w = Widget(code="99rbln", weight=1)
>>> w.save()
>>> v = Vehicle(make='Pontiac', model='Fiero', year='1987')
>>> v.save()

# The connections argument may be passed to commit, rollback, and the
# commit_on_success decorator as a keyword argument, as the first (for
# commit and rollback) or second (for the decorator) positional
# argument. It may be passed as a ConnectionInfo object, a connection
# (DatabaseWrapper) object, a connection name, or a list or dict of
# ConnectionInfo objects, connection objects, or connection names. If a
# dict is passed, the keys are ignored and the values used as the list
# of connections to commit, rollback, etc.

>>> transaction.commit(connections['_b'])
>>> transaction.commit('_b')
>>> transaction.commit(connections='_b')
>>> transaction.commit(connections=['_b'])
>>> transaction.commit(['_a', '_b'])
>>> transaction.commit(connections)

# When the connections argument is omitted entirely, the transaction
# command applies to all connections. Here we have committed
# connections 'django_test_db_a' and 'django_test_db_b', but not the
# default connection, so the new vehicle is lost on rollback.

>>> transaction.rollback()
>>> list(Artist.objects.all())
[<Artist: Paul Klee>, <Artist: Joan Miro>, <Artist: Pablo Picasso>]
>>> list(Widget.objects.all())
[<Widget: 100x2r>, <Widget: 99rbln>]
>>> list(Vehicle.objects.all())
[<Vehicle: 1966 Chevy Camaro>]
>>> transaction.rollback()
>>> transaction.managed(False)
>>> transaction.leave_transaction_management()

# Of course, relations and all other normal database operations work
# with models that use named connections just the same as with models
# that use the default connection. The only caveat is that you can't
# use a relation between two models that are stored in different
# databases. Note that that doesn't mean that two models using
# different connection *names* can't be related; only that in the the
# context in which they are used, if you use the relation, the
# connections named by the two models must resolve to the same
# database.

>>> a = Artist.objects.get(name="Paul Klee")
>>> list(a.opus_set.all())
[]
>>> a.opus_set.create(name="Magic Garden", year="1926")
<Opus: Magic Garden (1926)>
>>> list(a.opus_set.all())
[<Opus: Magic Garden (1926)>]
>>> d = DooHickey(name='Thing')
>>> d.save()
>>> d.widgets.create(code='d101', weight=92)
<Widget: d101>
>>> list(d.widgets.all())
[<Widget: d101>]
>>> w = Widget.objects.get(code='d101')
>>> list(w.doohickeys.all())
[<DooHickey: Thing>]
"""}

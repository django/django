from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os

class Animal(models.Model):
    name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)
    count = models.IntegerField()
    weight = models.FloatField()

    # use a non-default name for the default manager
    specimens = models.Manager()

    def __unicode__(self):
        return self.name

def animal_pre_save_check(signal, sender, instance, **kwargs):
    "A signal that is used to check the type of data loaded from fixtures"
    print 'Count = %s (%s)' % (instance.count, type(instance.count))
    print 'Weight = %s (%s)' % (instance.weight, type(instance.weight))

class Plant(models.Model):
    name = models.CharField(max_length=150)

    class Meta:
        # For testing when upper case letter in app name; regression for #4057
        db_table = "Fixtures_regress_plant"

class Stuff(models.Model):
    name = models.CharField(max_length=20, null=True)
    owner = models.ForeignKey(User, null=True)

    def __unicode__(self):
        # Oracle doesn't distinguish between None and the empty string.
        # This hack makes the test case pass using Oracle.
        name = self.name
        if settings.DATABASE_ENGINE == 'oracle' and name == u'':
            name = None
        return unicode(name) + u' is owned by ' + unicode(self.owner)

class Absolute(models.Model):
    name = models.CharField(max_length=40)

    load_count = 0

    def __init__(self, *args, **kwargs):
        super(Absolute, self).__init__(*args, **kwargs)
        Absolute.load_count += 1

class Parent(models.Model):
    name = models.CharField(max_length=10)

class Child(Parent):
    data = models.CharField(max_length=10)

# Models to regression test #7572
class Channel(models.Model):
    name = models.CharField(max_length=255)

class Article(models.Model):
    title = models.CharField(max_length=255)
    channels = models.ManyToManyField(Channel)

    class Meta:
        ordering = ('id',)

# Models to regression test #11428
class Widget(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

class WidgetProxy(Widget):
    class Meta:
        proxy = True

# Check for forward references in FKs and M2Ms with natural keys

class TestManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(name=key)

class Store(models.Model):
    objects = TestManager()
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

class Person(models.Model):
    objects = TestManager()
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    # Person doesn't actually have a dependency on store, but we need to define
    # one to test the behaviour of the dependency resolution algorithm.
    def natural_key(self):
        return (self.name,)
    natural_key.dependencies = ['fixtures_regress.store']

class Book(models.Model):
    name = models.CharField(max_length=255)
    author = models.ForeignKey(Person)
    stores = models.ManyToManyField(Store)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return u'%s by %s (available at %s)' % (
            self.name,
            self.author.name,
            ', '.join(s.name for s in self.stores.all())
        )

__test__ = {'API_TESTS':"""
>>> from django.core import management

# Load a fixture that uses PK=1
>>> management.call_command('loaddata', 'sequence', verbosity=0)

# Create a new animal. Without a sequence reset, this new object
# will take a PK of 1 (on Postgres), and the save will fail.
# This is a regression test for ticket #3790.
>>> animal = Animal(name='Platypus', latin_name='Ornithorhynchus anatinus', count=2, weight=2.3)
>>> animal.save()

###############################################
# Regression test for ticket #4558 -- pretty printing of XML fixtures
# doesn't affect parsing of None values.

# Load a pretty-printed XML fixture with Nulls.
>>> management.call_command('loaddata', 'pretty.xml', verbosity=0)
>>> Stuff.objects.all()
[<Stuff: None is owned by None>]

###############################################
# Regression test for ticket #6436 --
# os.path.join will throw away the initial parts of a path if it encounters
# an absolute path. This means that if a fixture is specified as an absolute path,
# we need to make sure we don't discover the absolute path in every fixture directory.

>>> load_absolute_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'absolute.json')
>>> management.call_command('loaddata', load_absolute_path, verbosity=0)
>>> Absolute.load_count
1

###############################################
# Test for ticket #4371 -- fixture loading fails silently in testcases
# Validate that error conditions are caught correctly

# redirect stderr for the next few tests...
>>> import sys
>>> savestderr = sys.stderr
>>> sys.stderr = sys.stdout

# Loading data of an unknown format should fail
>>> management.call_command('loaddata', 'bad_fixture1.unkn', verbosity=0)
Problem installing fixture 'bad_fixture1': unkn is not a known serialization format.

# Loading a fixture file with invalid data using explicit filename
>>> management.call_command('loaddata', 'bad_fixture2.xml', verbosity=0)
No fixture data found for 'bad_fixture2'. (File format may be invalid.)

# Loading a fixture file with invalid data without file extension
>>> management.call_command('loaddata', 'bad_fixture2', verbosity=0)
No fixture data found for 'bad_fixture2'. (File format may be invalid.)

# Loading a fixture file with no data returns an error
>>> management.call_command('loaddata', 'empty', verbosity=0)
No fixture data found for 'empty'. (File format may be invalid.)

# If any of the fixtures contain an error, loading is aborted
# (Regression for #9011 - error message is correct)
>>> management.call_command('loaddata', 'bad_fixture2', 'animal', verbosity=0)
No fixture data found for 'bad_fixture2'. (File format may be invalid.)

>>> sys.stderr = savestderr

###############################################
# Test for ticket #7565 -- PostgreSQL sequence resetting checks shouldn't
# ascend to parent models when inheritance is used (since they are treated
# individually).

>>> management.call_command('loaddata', 'model-inheritance.json', verbosity=0)

###############################################
# Test for ticket #7572 -- MySQL has a problem if the same connection is
# used to create tables, load data, and then query over that data.
# To compensate, we close the connection after running loaddata.
# This ensures that a new connection is opened when test queries are issued.

>>> management.call_command('loaddata', 'big-fixture.json', verbosity=0)

>>> articles = Article.objects.exclude(id=9)
>>> articles.values_list('id', flat=True)
[1, 2, 3, 4, 5, 6, 7, 8]

# Just for good measure, run the same query again. Under the influence of
# ticket #7572, this will give a different result to the previous call.
>>> articles.values_list('id', flat=True)
[1, 2, 3, 4, 5, 6, 7, 8]

###############################################
# Test for tickets #8298, #9942 - Field values should be coerced into the
# correct type by the deserializer, not as part of the database write.

>>> models.signals.pre_save.connect(animal_pre_save_check)
>>> management.call_command('loaddata', 'animal.xml', verbosity=0)
Count = 42 (<type 'int'>)
Weight = 1.2 (<type 'float'>)

>>> models.signals.pre_save.disconnect(animal_pre_save_check)

###############################################
# Regression for #11286 -- Ensure that dumpdata honors the default manager
# Dump the current contents of the database as a JSON fixture
>>> management.call_command('dumpdata', 'fixtures_regress.animal', format='json')
[{"pk": 1, "model": "fixtures_regress.animal", "fields": {"count": 3, "weight": 1.2, "name": "Lion", "latin_name": "Panthera leo"}}, {"pk": 2, "model": "fixtures_regress.animal", "fields": {"count": 2, "weight": 2.29..., "name": "Platypus", "latin_name": "Ornithorhynchus anatinus"}}, {"pk": 10, "model": "fixtures_regress.animal", "fields": {"count": 42, "weight": 1.2, "name": "Emu", "latin_name": "Dromaius novaehollandiae"}}]

###############################################
# Regression for #11428 - Proxy models aren't included
# when you run dumpdata over an entire app

# Flush out the database first
>>> management.call_command('reset', 'fixtures_regress', interactive=False, verbosity=0)

# Create an instance of the concrete class
>>> Widget(name='grommet').save()

# Dump data for the entire app. The proxy class shouldn't be included
>>> management.call_command('dumpdata', 'fixtures_regress', format='json')
[{"pk": 1, "model": "fixtures_regress.widget", "fields": {"name": "grommet"}}]

###############################################
# Check that natural key requirements are taken into account
# when serializing models
>>> management.call_command('loaddata', 'forward_ref_lookup.json', verbosity=0)

>>> management.call_command('dumpdata', 'fixtures_regress.book', 'fixtures_regress.person', 'fixtures_regress.store', verbosity=0, use_natural_keys=True)
[{"pk": 2, "model": "fixtures_regress.store", "fields": {"name": "Amazon"}}, {"pk": 3, "model": "fixtures_regress.store", "fields": {"name": "Borders"}}, {"pk": 4, "model": "fixtures_regress.person", "fields": {"name": "Neal Stephenson"}}, {"pk": 1, "model": "fixtures_regress.book", "fields": {"stores": [["Amazon"], ["Borders"]], "name": "Cryptonomicon", "author": ["Neal Stephenson"]}}]

# Now lets check the dependency sorting explicitly

# First Some models with pathological circular dependencies
>>> class Circle1(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.circle2']

>>> class Circle2(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.circle1']

>>> class Circle3(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.circle3']

>>> class Circle4(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.circle5']

>>> class Circle5(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.circle6']

>>> class Circle6(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.circle4']

>>> class ExternalDependency(models.Model):
...     name = models.CharField(max_length=255)
...     def natural_key(self):
...         return self.name
...     natural_key.dependencies = ['fixtures_regress.book']

# It doesn't matter what order you mention the models
# Store *must* be serialized before then Person, and both
# must be serialized before Book.
>>> from django.core.management.commands.dumpdata import sort_dependencies
>>> sort_dependencies([('fixtures_regress', [Book, Person, Store])])
[<class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

>>> sort_dependencies([('fixtures_regress', [Book, Store, Person])])
[<class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

>>> sort_dependencies([('fixtures_regress', [Store, Book, Person])])
[<class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

>>> sort_dependencies([('fixtures_regress', [Store, Person, Book])])
[<class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

>>> sort_dependencies([('fixtures_regress', [Person, Book, Store])])
[<class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

>>> sort_dependencies([('fixtures_regress', [Person, Store, Book])])
[<class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

# A dangling dependency - assume the user knows what they are doing.
>>> sort_dependencies([('fixtures_regress', [Person, Circle1, Store, Book])])
[<class 'regressiontests.fixtures_regress.models.Circle1'>, <class 'regressiontests.fixtures_regress.models.Store'>, <class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>]

# A tight circular dependency
>>> sort_dependencies([('fixtures_regress', [Person, Circle2, Circle1, Store, Book])])
Traceback (most recent call last):
...
CommandError: Can't resolve dependencies for fixtures_regress.Circle1, fixtures_regress.Circle2 in serialized app list.

>>> sort_dependencies([('fixtures_regress', [Circle1, Book, Circle2])])
Traceback (most recent call last):
...
CommandError: Can't resolve dependencies for fixtures_regress.Circle1, fixtures_regress.Circle2 in serialized app list.

# A self referential dependency
>>> sort_dependencies([('fixtures_regress', [Book, Circle3])])
Traceback (most recent call last):
...
CommandError: Can't resolve dependencies for fixtures_regress.Circle3 in serialized app list.

# A long circular dependency
>>> sort_dependencies([('fixtures_regress', [Person, Circle2, Circle1, Circle3, Store, Book])])
Traceback (most recent call last):
...
CommandError: Can't resolve dependencies for fixtures_regress.Circle1, fixtures_regress.Circle2, fixtures_regress.Circle3 in serialized app list.

# A dependency on a normal, non-natural-key model
>>> sort_dependencies([('fixtures_regress', [Person, ExternalDependency, Book])])
[<class 'regressiontests.fixtures_regress.models.Person'>, <class 'regressiontests.fixtures_regress.models.Book'>, <class 'regressiontests.fixtures_regress.models.ExternalDependency'>]

###############################################
# Check that normal primary keys still work
# on a model with natural key capabilities

>>> management.call_command('loaddata', 'non_natural_1.json', verbosity=0)
>>> management.call_command('loaddata', 'non_natural_2.xml', verbosity=0)

>>> Book.objects.all()
[<Book: Cryptonomicon by Neal Stephenson (available at Amazon, Borders)>, <Book: Ender's Game by Orson Scott Card (available at Collins Bookstore)>, <Book: Permutation City by Greg Egan (available at Angus and Robertson)>]

"""}


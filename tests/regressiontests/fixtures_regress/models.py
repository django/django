from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os

class Animal(models.Model):
    name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)
    count = models.IntegerField()
    
    def __unicode__(self):
        return self.common_name

def animal_pre_save_check(signal, sender, instance, **kwargs):
    "A signal that is used to check the type of data loaded from fixtures"
    print 'Count = %s (%s)' % (instance.count, type(instance.count))

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

# Models to regresison check #7572
class Channel(models.Model):
    name = models.CharField(max_length=255)

class Article(models.Model):
    title = models.CharField(max_length=255)
    channels = models.ManyToManyField(Channel)
    
    class Meta:
        ordering = ('id',)

__test__ = {'API_TESTS':"""
>>> from django.core import management

# Load a fixture that uses PK=1
>>> management.call_command('loaddata', 'sequence', verbosity=0)

# Create a new animal. Without a sequence reset, this new object
# will take a PK of 1 (on Postgres), and the save will fail.
# This is a regression test for ticket #3790.
>>> animal = Animal(name='Platypus', latin_name='Ornithorhynchus anatinus', count=2)
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
# Test for ticket #8298 - Field values should be coerced into the correct type
# by the deserializer, not as part of the database write.

>>> models.signals.pre_save.connect(animal_pre_save_check)
>>> management.call_command('loaddata', 'animal.xml', verbosity=0)
Count = 42 (<type 'int'>)

>>> models.signals.pre_save.disconnect(animal_pre_save_check)

"""}

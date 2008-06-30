from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os

class Animal(models.Model):
    name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)

    def __unicode__(self):
        return self.common_name

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


__test__ = {'API_TESTS':"""
>>> from django.core import management

# Load a fixture that uses PK=1
>>> management.call_command('loaddata', 'sequence', verbosity=0)

# Create a new animal. Without a sequence reset, this new object
# will take a PK of 1 (on Postgres), and the save will fail.
# This is a regression test for ticket #3790.
>>> animal = Animal(name='Platypus', latin_name='Ornithorhynchus anatinus')
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

"""}

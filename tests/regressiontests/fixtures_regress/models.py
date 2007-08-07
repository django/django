from django.db import models
from django.contrib.auth.models import User

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
        return unicode(self.name) + u' is owned by ' + unicode(self.owner)

__test__ = {'API_TESTS':"""
>>> from django.core import management

# Load a fixture that uses PK=1
>>> management.load_data(['sequence'], verbosity=0)
        
# Create a new animal. Without a sequence reset, this new object
# will take a PK of 1 (on Postgres), and the save will fail.
# This is a regression test for ticket #3790.
>>> animal = Animal(name='Platypus', latin_name='Ornithorhynchus anatinus')
>>> animal.save()

###############################################
# Regression test for ticket #4558 -- pretty printing of XML fixtures
# doesn't affect parsing of None values.

# Load a pretty-printed XML fixture with Nulls.
>>> management.load_data(['pretty.xml'], verbosity=0)
>>> Stuff.objects.all()
[<Stuff: None is owned by None>]

"""}

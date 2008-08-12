# coding: utf-8
"""
27. Default manipulators

Each model gets an ``AddManipulator`` and ``ChangeManipulator`` by default.
"""

from django.db import models

class Musician(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Album(models.Model):
    name = models.CharField(max_length=100)
    musician = models.ForeignKey(Musician)
    release_date = models.DateField(blank=True, null=True)

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS':u"""
>>> from django.utils.datastructures import MultiValueDict

# Create a Musician object via the default AddManipulator.
>>> man = Musician.AddManipulator()
>>> data = MultiValueDict({'first_name': ['Ella'], 'last_name': ['Fitzgerald']})

>>> man.get_validation_errors(data)
{}
>>> man.do_html2python(data)
>>> m1 = man.save(data)

# Verify it worked.
>>> Musician.objects.all()
[<Musician: Ella Fitzgerald>]
>>> [m1] == list(Musician.objects.all())
True

# Attempt to add a Musician without a first_name.
>>> man.get_validation_errors(MultiValueDict({'last_name': ['Blakey']}))['first_name']
[u'This field is required.']

# Attempt to add a Musician without a first_name and last_name.
>>> errors = man.get_validation_errors(MultiValueDict({}))
>>> errors['first_name']
[u'This field is required.']
>>> errors['last_name']
[u'This field is required.']

# Attempt to create an Album without a name or musician.
>>> man = Album.AddManipulator()
>>> errors = man.get_validation_errors(MultiValueDict({}))
>>> errors['musician']
[u'This field is required.']
>>> errors['name']
[u'This field is required.']

# Attempt to create an Album with an invalid musician.
>>> errors = man.get_validation_errors(MultiValueDict({'name': ['Sallies Fforth'], 'musician': ['foo']}))
>>> errors['musician']
[u"Select a valid choice; 'foo' is not in [u'', u'1']."]

# Attempt to create an Album with an invalid release_date.
>>> errors = man.get_validation_errors(MultiValueDict({'name': ['Sallies Fforth'], 'musician': ['1'], 'release_date': 'today'}))
>>> errors['release_date']
[u'Enter a valid date in YYYY-MM-DD format.']

# Create an Album without a release_date (because it's optional).
>>> data = MultiValueDict({'name': ['Ella and Basie'], 'musician': ['1']})
>>> man.get_validation_errors(data)
{}
>>> man.do_html2python(data)
>>> a1 = man.save(data)

# Verify it worked.
>>> Album.objects.all()
[<Album: Ella and Basie>]
>>> Album.objects.get().musician
<Musician: Ella Fitzgerald>

# Create an Album with a release_date.
>>> data = MultiValueDict({'name': ['Ultimate Ella'], 'musician': ['1'], 'release_date': ['2005-02-13']})
>>> man.get_validation_errors(data)
{}
>>> man.do_html2python(data)
>>> a2 = man.save(data)

# Verify it worked.
>>> Album.objects.order_by('name')
[<Album: Ella and Basie>, <Album: Ultimate Ella>]
>>> a2 = Album.objects.get(pk=2)
>>> a2
<Album: Ultimate Ella>
>>> a2.release_date
datetime.date(2005, 2, 13)

# Test isValidFloat Unicode coercion
>>> from django.core.validators import isValidFloat, ValidationError
>>> try: isValidFloat(u"ä", None)
... except ValidationError: pass
"""}

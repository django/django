"""
27. Default manipulators

Each model gets an AddManipulator and ChangeManipulator by default.
"""

from django.db import models

class Musician(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Album(models.Model):
    name = models.CharField(maxlength=100)
    musician = models.ForeignKey(Musician)
    release_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

__test__ = {'API_TESTS':"""
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
>>> man.get_validation_errors(MultiValueDict({'last_name': ['Blakey']}))
{'first_name': [u'This field is required.']}

# Attempt to add a Musician without a first_name and last_name.
>>> man.get_validation_errors(MultiValueDict({}))
{'first_name': [u'This field is required.'], 'last_name': [u'This field is required.']}

# Attempt to create an Album without a name or musician.
>>> man = Album.AddManipulator()
>>> man.get_validation_errors(MultiValueDict({}))
{'musician': [u'This field is required.'], 'name': [u'This field is required.']}

# Attempt to create an Album with an invalid musician.
>>> man.get_validation_errors(MultiValueDict({'name': ['Sallies Fforth'], 'musician': ['foo']}))
{'musician': [u"Select a valid choice; 'foo' is not in ['', '1']."]}

# Attempt to create an Album with an invalid release_date.
>>> man.get_validation_errors(MultiValueDict({'name': ['Sallies Fforth'], 'musician': ['1'], 'release_date': 'today'}))
{'release_date': [u'Enter a valid date in YYYY-MM-DD format.']}

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
"""}

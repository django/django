"""
33. get_or_create()

``get_or_create()`` does what it says: it tries to look up an object with the
given parameters. If an object isn't found, it creates one with the given
parameters.
"""

from django.db import models, IntegrityError

class Person(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birthday = models.DateField()

    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)

class ManualPrimaryKeyTest(models.Model):
    id = models.IntegerField(primary_key=True)
    data = models.CharField(max_length=100)

__test__ = {'API_TESTS':"""
# Acting as a divine being, create an Person.
>>> from datetime import date
>>> p = Person(first_name='John', last_name='Lennon', birthday=date(1940, 10, 9))
>>> p.save()

# Only one Person is in the database at this point.
>>> Person.objects.count()
1

# get_or_create() a person with similar first names.
>>> p, created = Person.objects.get_or_create(first_name='John', last_name='Lennon', defaults={'birthday': date(1940, 10, 9)})

# get_or_create() didn't have to create an object.
>>> created
False

# There's still only one Person in the database.
>>> Person.objects.count()
1

# get_or_create() a Person with a different name.
>>> p, created = Person.objects.get_or_create(first_name='George', last_name='Harrison', defaults={'birthday': date(1943, 2, 25)})
>>> created
True
>>> Person.objects.count()
2

# If we execute the exact same statement, it won't create a Person.
>>> p, created = Person.objects.get_or_create(first_name='George', last_name='Harrison', defaults={'birthday': date(1943, 2, 25)})
>>> created
False
>>> Person.objects.count()
2

# If you don't specify a value or default value for all required fields, you
# will get an error.
>>> try:
...     p, created = Person.objects.get_or_create(first_name='Tom', last_name='Smith')
... except Exception, e:
...     if isinstance(e, IntegrityError):
...         print "Pass"
...     else:
...         print "Fail with %s" % type(e)
Pass

# If you specify an existing primary key, but different other fields, then you
# will get an error and data will not be updated.
>>> m = ManualPrimaryKeyTest(id=1, data='Original')
>>> m.save()
>>> try:
...    m, created = ManualPrimaryKeyTest.objects.get_or_create(id=1, data='Different')
... except Exception, e:
...    if isinstance(e, IntegrityError):
...        print "Pass"
...    else:
...        print "Fail with %s" % type(e)
Pass
>>> ManualPrimaryKeyTest.objects.get(id=1).data == 'Original'
True
"""}

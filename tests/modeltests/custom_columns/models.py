"""
17. Custom column names

If your database column name is different than your model attribute, use the
``db_column`` parameter. Note that you'll use the field's name, not its column
name, in API usage.
"""

from django.db import models

class Person(models.Model):
    first_name = models.CharField(maxlength=30, db_column='firstname')
    last_name = models.CharField(maxlength=30, db_column='last')

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

__test__ = {'API_TESTS':"""
# Create a Person.
>>> p = Person(first_name='John', last_name='Smith')
>>> p.save()

>>> p.id
1

>>> Person.objects.all()
[<Person: John Smith>]

>>> Person.objects.filter(first_name__exact='John')
[<Person: John Smith>]

>>> Person.objects.get(first_name__exact='John')
<Person: John Smith>

>>> Person.objects.filter(firstname__exact='John')
Traceback (most recent call last):
    ...
TypeError: Cannot resolve keyword 'firstname' into field

>>> p = Person.objects.get(last_name__exact='Smith')
>>> p.first_name
'John'
>>> p.last_name
'Smith'
>>> p.firstname
Traceback (most recent call last):
    ...
AttributeError: 'Person' object has no attribute 'firstname'
>>> p.last
Traceback (most recent call last):
    ...
AttributeError: 'Person' object has no attribute 'last'
"""}

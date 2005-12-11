"""
17. Custom column names

If your database column name is different than your model attribute, use the
``db_column`` parameter. Note that you'll use the field's name, not its column
name, in API usage.
"""

from django.core import meta

class Person(meta.Model):
    first_name = meta.CharField(maxlength=30, db_column='firstname')
    last_name = meta.CharField(maxlength=30, db_column='last')

    def __repr__(self):
        return '%s %s' % (self.first_name, self.last_name)

API_TESTS = """
# Create a Person.
>>> p = Person(first_name='John', last_name='Smith')
>>> p.save()

>>> p.id
1

>>> Person.objects.get_list()
[John Smith]

>>> Person.objects.get_list(first_name__exact='John')
[John Smith]

>>> Person.objects.get_object(first_name__exact='John')
John Smith

>>> Person.objects.get_list(firstname__exact='John')
Traceback (most recent call last):
    ...
TypeError: got unexpected keyword argument 'firstname__exact'

>>> p = Person.objects.get_object(last_name__exact='Smith')
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
"""

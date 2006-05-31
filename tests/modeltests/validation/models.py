"""
29. Validation

This is an experimental feature!

Each model instance has a validate() method that returns a dictionary of
validation errors in the instance's fields. This method has a side effect
of converting each field to its appropriate Python data type.
"""

from django.db import models

class Person(models.Model):
    is_child = models.BooleanField()
    name = models.CharField(maxlength=20)
    birthdate = models.DateField()
    favorite_moment = models.DateTimeField()
    email = models.EmailField()

    def __repr__(self):
        return self.name

API_TESTS = """

>>> import datetime
>>> valid_params = {
...     'is_child': True,
...     'name': 'John',
...     'birthdate': datetime.date(2000, 5, 3),
...     'favorite_moment': datetime.datetime(2002, 4, 3, 13, 23),
...     'email': 'john@example.com'
... }
>>> p = Person(**valid_params)
>>> p.validate()
{}

>>> p = Person(**dict(valid_params, id='23'))
>>> p.validate()
{}
>>> p.id
23

>>> p = Person(**dict(valid_params, id='foo'))
>>> p.validate()
{'id': ['This value must be an integer.']}

>>> p = Person(**dict(valid_params, id=None))
>>> p.validate()
{}
>>> repr(p.id)
'None'

>>> p = Person(**dict(valid_params, is_child='t'))
>>> p.validate()
{}
>>> p.is_child
True

>>> p = Person(**dict(valid_params, is_child='f'))
>>> p.validate()
{}
>>> p.is_child
False

>>> p = Person(**dict(valid_params, is_child=True))
>>> p.validate()
{}
>>> p.is_child
True

>>> p = Person(**dict(valid_params, is_child=False))
>>> p.validate()
{}
>>> p.is_child
False

>>> p = Person(**dict(valid_params, is_child='foo'))
>>> p.validate()
{'is_child': ['This value must be either True or False.']}

>>> p = Person(**dict(valid_params, name=u'Jose'))
>>> p.validate()
{}
>>> p.name
u'Jose'

>>> p = Person(**dict(valid_params, name=227))
>>> p.validate()
{}
>>> p.name
'227'

>>> p = Person(**dict(valid_params, birthdate=datetime.date(2000, 5, 3)))
>>> p.validate()
{}
>>> p.birthdate
datetime.date(2000, 5, 3)

>>> p = Person(**dict(valid_params, birthdate=datetime.datetime(2000, 5, 3)))
>>> p.validate()
{}
>>> p.birthdate
datetime.date(2000, 5, 3)

>>> p = Person(**dict(valid_params, birthdate='2000-05-03'))
>>> p.validate()
{}
>>> p.birthdate
datetime.date(2000, 5, 3)

>>> p = Person(**dict(valid_params, birthdate='2000-5-3'))
>>> p.validate()
{}
>>> p.birthdate
datetime.date(2000, 5, 3)

>>> p = Person(**dict(valid_params, birthdate='foo'))
>>> p.validate()
{'birthdate': ['Enter a valid date in YYYY-MM-DD format.']}

>>> p = Person(**dict(valid_params, favorite_moment=datetime.datetime(2002, 4, 3, 13, 23)))
>>> p.validate()
{}
>>> p.favorite_moment
datetime.datetime(2002, 4, 3, 13, 23)

>>> p = Person(**dict(valid_params, favorite_moment=datetime.datetime(2002, 4, 3)))
>>> p.validate()
{}
>>> p.favorite_moment
datetime.datetime(2002, 4, 3, 0, 0)

>>> p = Person(**dict(valid_params, email='john@example.com'))
>>> p.validate()
{}
>>> p.email
'john@example.com'

>>> p = Person(**dict(valid_params, email=u'john@example.com'))
>>> p.validate()
{}
>>> p.email
u'john@example.com'

>>> p = Person(**dict(valid_params, email=22))
>>> p.validate()
{'email': ['Enter a valid e-mail address.']}

"""

"""
>>> from django.db.models.fields import *

# DecimalField

>>> f = DecimalField()

>>> f.to_python(3)
Decimal("3")

>>> f.to_python("3.14")
Decimal("3.14")

>>> f.to_python("abc")
Traceback (most recent call last):
...
ValidationError: [u'This value must be a decimal number.']

>>> f = DecimalField(max_digits=5, decimal_places=1)
>>> x = f.to_python(2)
>>> y = f.to_python('2.6')

>>> f.get_db_prep_save(x)
u'2.0'
>>> f.get_db_prep_save(y)
u'2.6'
>>> f.get_db_prep_save(None)
>>> f.get_db_prep_lookup('exact', x)
[u'2.0']
>>> f.get_db_prep_lookup('exact', y)
[u'2.6']
>>> f.get_db_prep_lookup('exact', None)
[None]

"""

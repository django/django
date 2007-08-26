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
"""

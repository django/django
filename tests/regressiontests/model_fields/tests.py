"""
>>> from django.db.models.fields import *

# DecimalField

>>> f = DecimalField(max_digits=4, decimal_places=2)

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

>>> f._format(x)
u'2.0'
>>> f._format(y)
u'2.6'
>>> f._format(None)
>>> f.get_db_prep_lookup('exact', None)
[None]

# DateTimeField and TimeField to_python should support usecs:
>>> f = DateTimeField()
>>> f.to_python('2001-01-02 03:04:05.000006')
datetime.datetime(2001, 1, 2, 3, 4, 5, 6)
>>> f.to_python('2001-01-02 03:04:05.999999')
datetime.datetime(2001, 1, 2, 3, 4, 5, 999999)

>>> f = TimeField()
>>> f.to_python('01:02:03.000004')
datetime.time(1, 2, 3, 4)
>>> f.to_python('01:02:03.999999')
datetime.time(1, 2, 3, 999999)


"""

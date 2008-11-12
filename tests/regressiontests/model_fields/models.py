
from django.db import models

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal    # Python 2.3 fallback

class Foo(models.Model):
    a = models.CharField(max_length=10)
    d = models.DecimalField(max_digits=5, decimal_places=3)

def get_foo():
    return Foo.objects.get(id=1)

class Bar(models.Model):
    b = models.CharField(max_length=10)
    a = models.ForeignKey(Foo, default=get_foo)

class Whiz(models.Model):
    CHOICES = (
        ('Group 1', (
                (1,'First'),
                (2,'Second'),
            )
        ),
        ('Group 2', (
                (3,'Third'),
                (4,'Fourth'),
            )
        ),
        (0,'Other'),
    )
    c = models.IntegerField(choices=CHOICES, null=True)
    
class BigD(models.Model):
    d = models.DecimalField(max_digits=38, decimal_places=30)

__test__ = {'API_TESTS':"""
# Create a couple of Places.
>>> f = Foo.objects.create(a='abc', d=decimal.Decimal("12.34"))
>>> f.id
1
>>> b = Bar(b = "bcd")
>>> b.a
<Foo: Foo object>
>>> b.save()

# Regression tests for #7913
# Check that get_choices and get_flatchoices interact with
# get_FIELD_display to return the expected values.

# Test a nested value
>>> w = Whiz(c=1)
>>> w.save()
>>> w.get_c_display()
u'First'

# Test a top level value
>>> w.c = 0
>>> w.get_c_display()
u'Other'

# Test an invalid data value
>>> w.c = 9
>>> w.get_c_display()
9

# Test a blank data value
>>> w.c = None
>>> print w.get_c_display()
None

# Test an empty data value
>>> w.c = ''
>>> w.get_c_display()
u''

# Regression test for #8023: should be able to filter decimal fields using
# strings (which is what gets passed through from, e.g., the admin interface).
>>> Foo.objects.filter(d=u'1.23')
[]

# Regression test for #5079 -- ensure decimals don't go through a corrupting
# float conversion during save.  
>>> bd = BigD(d="12.9")
>>> bd.save()
>>> bd = BigD.objects.get(pk=bd.pk)
>>> bd.d == decimal.Decimal("12.9")
True
"""}

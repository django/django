
from django.db import models

class Foo(models.Model):
    a = models.CharField(max_length=10)

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
    
__test__ = {'API_TESTS':"""
# Create a couple of Places.
>>> f = Foo.objects.create(a='abc')
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


"""}

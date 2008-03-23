
from django.db import models

class Foo(models.Model):
    a = models.CharField(max_length=10)

def get_foo():
    return Foo.objects.get(id=1)

class Bar(models.Model):
    b = models.CharField(max_length=10)
    a = models.ForeignKey(Foo, default=get_foo)

__test__ = {'API_TESTS':"""
# Create a couple of Places.
>>> f = Foo.objects.create(a='abc')
>>> f.id
1
>>> b = Bar(b = "bcd")
>>> b.a
<Foo: Foo object>
>>> b.save()

"""}

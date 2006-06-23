from django.db import models

class Foo(models.Model):
    name = models.CharField(maxlength=50)

    def __str__(self):
        return "Foo %s" % self.name

class Bar(models.Model):
    name = models.CharField(maxlength=50)
    normal = models.ForeignKey(Foo, related_name='normal_foo')
    fwd = models.ForeignKey("Whiz")
    back = models.ForeignKey("Foo")

    def __str__(self):
        return "Bar %s" % self.place.name

class Whiz(models.Model):
    name = models.CharField(maxlength = 50)

    def __str__(self):
        return "Whiz %s" % self.name

API_TESTS = """
# Regression test for #1662: Check that string form referencing of models works, both as
# pre and post reference

>>> f1 = Foo(name="Foo1")
>>> f1.save()
>>> f2 = Foo(name="Foo1")
>>> f2.save()

>>> w1 = Whiz(name="Whiz1")
>>> w1.save()

>>> b1 = Bar(name="Bar1", normal=f1, fwd=w1, back=f2)
>>> b1.save()

>>> b1.normal
<Foo: Foo Foo1>

>>> b1.fwd
<Whiz: Whiz Whiz1>

>>> b1.back
<Foo: Foo Foo1>

"""

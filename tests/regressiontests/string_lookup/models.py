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

class Child(models.Model):
    parent = models.OneToOneField('Base')
    name = models.CharField(maxlength = 50)

    def __str__(self):
        return "Child %s" % self.name
    
class Base(models.Model):
    name = models.CharField(maxlength = 50)

    def __str__(self):
        return "Base %s" % self.name

__test__ = {'API_TESTS':"""
# Regression test for #1661 and #1662: Check that string form referencing of models works, 
# both as pre and post reference, on all RelatedField types.

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

>>> base1 = Base(name="Base1")
>>> base1.save()

>>> child1 = Child(name="Child1", parent=base1)
>>> child1.save()

>>> child1.parent
<Base: Base Base1>
"""}

# -*- coding: utf-8 -*-
from django.db import models

class Foo(models.Model):
    name = models.CharField(max_length=50)
    friend = models.CharField(max_length=50, blank=True)

    def __unicode__(self):
        return "Foo %s" % self.name

class Bar(models.Model):
    name = models.CharField(max_length=50)
    normal = models.ForeignKey(Foo, related_name='normal_foo')
    fwd = models.ForeignKey("Whiz")
    back = models.ForeignKey("Foo")

    def __unicode__(self):
        return "Bar %s" % self.place.name

class Whiz(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return "Whiz %s" % self.name

class Child(models.Model):
    parent = models.OneToOneField('Base')
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return "Child %s" % self.name

class Base(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return "Base %s" % self.name

class Article(models.Model):
    name = models.CharField(max_length=50)
    text = models.TextField()
    submitted_from = models.IPAddressField(blank=True, null=True)

    def __str__(self):
        return "Article %s" % self.name

__test__ = {'API_TESTS': ur"""
# Regression test for #1661 and #1662: Check that string form referencing of
# models works, both as pre and post reference, on all RelatedField types.

>>> f1 = Foo(name="Foo1")
>>> f1.save()
>>> f2 = Foo(name="Foo2")
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
<Foo: Foo Foo2>

>>> base1 = Base(name="Base1")
>>> base1.save()

>>> child1 = Child(name="Child1", parent=base1)
>>> child1.save()

>>> child1.parent
<Base: Base Base1>

# Regression tests for #3937: make sure we can use unicode characters in
# queries.
# BUG: These tests fail on MySQL, but it's a problem with the test setup. A
# properly configured UTF-8 database can handle this.

>>> fx = Foo(name='Bjorn', friend=u'François')
>>> fx.save()
>>> Foo.objects.get(friend__contains=u'\xe7')
<Foo: Foo Bjorn>

# We can also do the above query using UTF-8 strings.
>>> Foo.objects.get(friend__contains='\xc3\xa7')
<Foo: Foo Bjorn>

# Regression tests for #5087: make sure we can perform queries on TextFields.
>>> a = Article(name='Test', text='The quick brown fox jumps over the lazy dog.')
>>> a.save()
>>> Article.objects.get(text__exact='The quick brown fox jumps over the lazy dog.')
<Article: Article Test>

>>> Article.objects.get(text__contains='quick brown fox')
<Article: Article Test>

# Regression test for #708: "like" queries on IP address fields require casting
# to text (on PostgreSQL).
>>> Article(name='IP test', text='The body', submitted_from='192.0.2.100').save()
>>> Article.objects.filter(submitted_from__contains='192.0.2')
[<Article: Article IP test>]

"""}

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

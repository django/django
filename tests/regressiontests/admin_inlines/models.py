"""
Testing of admin inline formsets.

"""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class Parent(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class Teacher(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class Child(models.Model):
    name = models.CharField(max_length=50)
    teacher = models.ForeignKey(Teacher)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    parent = generic.GenericForeignKey()

    def __unicode__(self):
        return u'I am %s, a child of %s' % (self.name, self.parent)

__test__ = {'API_TESTS': """

# Regression test for #9362

>>> sally = Teacher.objects.create(name='Sally')
>>> john = Parent.objects.create(name='John')
>>> joe = Child.objects.create(name='Joe', teacher=sally, parent=john)

The problem depends only on InlineAdminForm and its "original" argument, so
we can safely set the other arguments to None/{}. We just need to check that
the content_type argument of Child isn't altered by the internals of the
inline form.

>>> from django.contrib.admin.helpers import InlineAdminForm
>>> iaf = InlineAdminForm(None, None, {}, {}, joe)
>>> iaf.original
<Child: I am Joe, a child of John>

"""
}
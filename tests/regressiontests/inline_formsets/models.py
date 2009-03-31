# coding: utf-8
from django.db import models

class School(models.Model):
    name = models.CharField(max_length=100)

class Parent(models.Model):
    name = models.CharField(max_length=100)

class Child(models.Model):
    mother = models.ForeignKey(Parent, related_name='mothers_children')
    father = models.ForeignKey(Parent, related_name='fathers_children')
    school = models.ForeignKey(School)
    name = models.CharField(max_length=100)

class Poet(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Poem(models.Model):
    poet = models.ForeignKey(Poet)
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS': """

>>> from django.forms.models import inlineformset_factory


Child has two ForeignKeys to Parent, so if we don't specify which one to use
for the inline formset, we should get an exception.

>>> ifs = inlineformset_factory(Parent, Child)
Traceback (most recent call last):
    ...
Exception: <class 'regressiontests.inline_formsets.models.Child'> has more than 1 ForeignKey to <class 'regressiontests.inline_formsets.models.Parent'>


These two should both work without a problem.

>>> ifs = inlineformset_factory(Parent, Child, fk_name='mother')
>>> ifs = inlineformset_factory(Parent, Child, fk_name='father')


If we specify fk_name, but it isn't a ForeignKey from the child model to the
parent model, we should get an exception.

>>> ifs = inlineformset_factory(Parent, Child, fk_name='school')
Traceback (most recent call last):
    ...
Exception: fk_name 'school' is not a ForeignKey to <class 'regressiontests.inline_formsets.models.Parent'>


If the field specified in fk_name is not a ForeignKey, we should get an
exception.

>>> ifs = inlineformset_factory(Parent, Child, fk_name='test')
Traceback (most recent call last):
    ...
Exception: <class 'regressiontests.inline_formsets.models.Child'> has no field named 'test'


# Regression test for #9171.
>>> ifs = inlineformset_factory(Parent, Child, exclude=('school',), fk_name='mother')
"""
}

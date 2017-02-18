"""
Testing of admin inline formsets.

"""
from __future__ import unicode_literals

import random

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Parent(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Teacher(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Child(models.Model):
    name = models.CharField(max_length=50)
    teacher = models.ForeignKey(Teacher)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    parent = GenericForeignKey()

    def __str__(self):
        return 'I am %s, a child of %s' % (self.name, self.parent)


class Book(models.Model):
    name = models.CharField(max_length=50)


class Author(models.Model):
    name = models.CharField(max_length=50)
    books = models.ManyToManyField(Book)


class NonAutoPKBook(models.Model):
    rand_pk = models.IntegerField(primary_key=True, editable=False)
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        while not self.rand_pk:
            test_pk = random.randint(1, 99999)
            if not NonAutoPKBook.objects.filter(rand_pk=test_pk).exists():
                self.rand_pk = test_pk
        super(NonAutoPKBook, self).save(*args, **kwargs)


class EditablePKBook(models.Model):
    manual_pk = models.IntegerField(primary_key=True)
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=50)


class Holder(models.Model):
    dummy = models.IntegerField()


class Inner(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder)
    readonly = models.CharField("Inner readonly label", max_length=1)

    def get_absolute_url(self):
        return '/inner/'


class Holder2(models.Model):
    dummy = models.IntegerField()


class Inner2(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder2)


class Holder3(models.Model):
    dummy = models.IntegerField()


class Inner3(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder3)

# Models for ticket #8190


class Holder4(models.Model):
    dummy = models.IntegerField()


class Inner4Stacked(models.Model):
    dummy = models.IntegerField(help_text="Awesome stacked help text is awesome.")
    holder = models.ForeignKey(Holder4)


class Inner4Tabular(models.Model):
    dummy = models.IntegerField(help_text="Awesome tabular help text is awesome.")
    holder = models.ForeignKey(Holder4)

# Models for #12749


class Person(models.Model):
    firstname = models.CharField(max_length=15)


class OutfitItem(models.Model):
    name = models.CharField(max_length=15)


class Fashionista(models.Model):
    person = models.OneToOneField(Person, primary_key=True)
    weaknesses = models.ManyToManyField(OutfitItem, through='ShoppingWeakness', blank=True)


class ShoppingWeakness(models.Model):
    fashionista = models.ForeignKey(Fashionista)
    item = models.ForeignKey(OutfitItem)

# Models for #13510


class TitleCollection(models.Model):
    pass


class Title(models.Model):
    collection = models.ForeignKey(TitleCollection, blank=True, null=True)
    title1 = models.CharField(max_length=100)
    title2 = models.CharField(max_length=100)

# Models for #15424


class Poll(models.Model):
    name = models.CharField(max_length=40)


class Question(models.Model):
    poll = models.ForeignKey(Poll)


class Novel(models.Model):
    name = models.CharField(max_length=40)


class Chapter(models.Model):
    name = models.CharField(max_length=40)
    novel = models.ForeignKey(Novel)


class FootNote(models.Model):
    """
    Model added for ticket 19838
    """
    chapter = models.ForeignKey(Chapter, on_delete=models.PROTECT)
    note = models.CharField(max_length=40)

# Models for #16838


class CapoFamiglia(models.Model):
    name = models.CharField(max_length=100)


class Consigliere(models.Model):
    name = models.CharField(max_length=100, help_text='Help text for Consigliere')
    capo_famiglia = models.ForeignKey(CapoFamiglia, related_name='+')


class SottoCapo(models.Model):
    name = models.CharField(max_length=100)
    capo_famiglia = models.ForeignKey(CapoFamiglia, related_name='+')


class ReadOnlyInline(models.Model):
    name = models.CharField(max_length=100, help_text='Help text for ReadOnlyInline')
    capo_famiglia = models.ForeignKey(CapoFamiglia)


# Models for #18433

class ParentModelWithCustomPk(models.Model):
    my_own_pk = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)


class ChildModel1(models.Model):
    my_own_pk = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(ParentModelWithCustomPk)

    def get_absolute_url(self):
        return '/child_model1/'


class ChildModel2(models.Model):
    my_own_pk = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(ParentModelWithCustomPk)

    def get_absolute_url(self):
        return '/child_model2/'


# Models for #19425
class BinaryTree(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True)

# Models for #19524


class LifeForm(models.Model):
    pass


class ExtraTerrestrial(LifeForm):
    name = models.CharField(max_length=100)


class Sighting(models.Model):
    et = models.ForeignKey(ExtraTerrestrial)
    place = models.CharField(max_length=100)


# Models for #18263
class SomeParentModel(models.Model):
    name = models.CharField(max_length=1)


class SomeChildModel(models.Model):
    name = models.CharField(max_length=1)
    position = models.PositiveIntegerField()
    parent = models.ForeignKey(SomeParentModel)

# Other models


class ProfileCollection(models.Model):
    pass


class Profile(models.Model):
    collection = models.ForeignKey(ProfileCollection, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

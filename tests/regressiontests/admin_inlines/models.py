"""
Testing of admin inline formsets.

"""
from django.db import models
from django.contrib import admin
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

class Book(models.Model):
    name = models.CharField(max_length=50)

class Author(models.Model):
    name = models.CharField(max_length=50)
    books = models.ManyToManyField(Book)

class BookInline(admin.TabularInline):
    model = Author.books.through

class AuthorAdmin(admin.ModelAdmin):
    inlines = [BookInline]

admin.site.register(Author, AuthorAdmin)

class Holder(models.Model):
    dummy = models.IntegerField()


class Inner(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder)
    readonly = models.CharField("Inner readonly label", max_length=1)


class InnerInline(admin.StackedInline):
    model = Inner
    can_delete = False
    readonly_fields = ('readonly',) # For bug #13174 tests.


class Holder2(models.Model):
    dummy = models.IntegerField()


class Inner2(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder2)

class HolderAdmin(admin.ModelAdmin):

    class Media:
        js = ('my_awesome_admin_scripts.js',)

class InnerInline2(admin.StackedInline):
    model = Inner2

    class Media:
        js = ('my_awesome_inline_scripts.js',)

class Holder3(models.Model):
    dummy = models.IntegerField()


class Inner3(models.Model):
    dummy = models.IntegerField()
    holder = models.ForeignKey(Holder3)

class InnerInline3(admin.StackedInline):
    model = Inner3

    class Media:
        js = ('my_awesome_inline_scripts.js',)

# Test bug #12561 and #12778
# only ModelAdmin media
admin.site.register(Holder, HolderAdmin, inlines=[InnerInline])
# ModelAdmin and Inline media
admin.site.register(Holder2, HolderAdmin, inlines=[InnerInline2])
# only Inline media
admin.site.register(Holder3, inlines=[InnerInline3])

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

class InlineWeakness(admin.TabularInline):
    model = ShoppingWeakness
    extra = 1

admin.site.register(Fashionista, inlines=[InlineWeakness])


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

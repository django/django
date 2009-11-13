"""
Tests of ModelAdmin validation logic.
"""

from django.db import models


class Album(models.Model):
    title = models.CharField(max_length=150)


class Song(models.Model):
    title = models.CharField(max_length=150)
    album = models.ForeignKey(Album)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return self.title


class TwoAlbumFKAndAnE(models.Model):
    album1 = models.ForeignKey(Album, related_name="album1_set")
    album2 = models.ForeignKey(Album, related_name="album2_set")
    e = models.CharField(max_length=1)


class Author(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    name = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author, through='AuthorsBooks')


class AuthorsBooks(models.Model):
    author = models.ForeignKey(Author)
    book = models.ForeignKey(Book)


__test__ = {'API_TESTS':"""

>>> from django import forms
>>> from django.contrib import admin
>>> from django.contrib.admin.validation import validate, validate_inline

# Regression test for #8027: custom ModelForms with fields/fieldsets

>>> class SongForm(forms.ModelForm):
...     pass

>>> class ValidFields(admin.ModelAdmin):
...     form = SongForm
...     fields = ['title']

>>> class InvalidFields(admin.ModelAdmin):
...     form = SongForm
...     fields = ['spam']

>>> validate(ValidFields, Song)
>>> validate(InvalidFields, Song)
Traceback (most recent call last):
    ...
ImproperlyConfigured: 'InvalidFields.fields' refers to field 'spam' that is missing from the form.

# Regression test for #9932 - exclude in InlineModelAdmin
# should not contain the ForeignKey field used in ModelAdmin.model

>>> class SongInline(admin.StackedInline):
...     model = Song
...     exclude = ['album']

>>> class AlbumAdmin(admin.ModelAdmin):
...     model = Album
...     inlines = [SongInline]

>>> validate(AlbumAdmin, Album)
Traceback (most recent call last):
    ...
ImproperlyConfigured: SongInline cannot exclude the field 'album' - this is the foreign key to the parent model Album.

# Regression test for #11709 - when testing for fk excluding (when exclude is
# given) make sure fk_name is honored or things blow up when there is more
# than one fk to the parent model.

>>> class TwoAlbumFKAndAnEInline(admin.TabularInline):
...     model = TwoAlbumFKAndAnE
...     exclude = ("e",)
...     fk_name = "album1"

>>> validate_inline(TwoAlbumFKAndAnEInline, None, Album)

# Ensure inlines validate that they can be used correctly.

>>> class TwoAlbumFKAndAnEInline(admin.TabularInline):
...     model = TwoAlbumFKAndAnE

>>> validate_inline(TwoAlbumFKAndAnEInline, None, Album)
Traceback (most recent call last):
    ...
Exception: <class 'regressiontests.admin_validation.models.TwoAlbumFKAndAnE'> has more than 1 ForeignKey to <class 'regressiontests.admin_validation.models.Album'>

>>> class TwoAlbumFKAndAnEInline(admin.TabularInline):
...     model = TwoAlbumFKAndAnE
...     fk_name = "album1"

>>> validate_inline(TwoAlbumFKAndAnEInline, None, Album)

# Regression test for #12203 - Fail more gracefully when a M2M field that
# specifies the 'through' option is included in the 'fields' ModelAdmin option.

>>> class BookAdmin(admin.ModelAdmin):
...     fields = ['authors']

>>> validate(BookAdmin, Book)
Traceback (most recent call last):
    ...
ImproperlyConfigured: 'BookAdmin.fields' can't include the ManyToManyField field 'authors' because 'authors' manually specifies a 'through' model.

# Regression test for #12209 -- If the explicitly provided through model
# is specified as a string, the admin should still be able use
# Model.m2m_field.through

>>> class AuthorsInline(admin.TabularInline):
...     model = Book.authors.through

>>> class BookAdmin(admin.ModelAdmin):
...     inlines = [AuthorsInline]

# If the through model is still a string (and hasn't been resolved to a model)
# the validation will fail.
>>> validate(BookAdmin, Book)

"""}

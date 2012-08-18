from __future__ import absolute_import

from django import forms

from .models import Author, Artist


class AuthorForm(forms.ModelForm):
    name = forms.CharField()
    slug = forms.SlugField()

    class Meta:
        model = Author


class ArtistForm(forms.ModelForm):
    name = forms.CharField()

    class Meta:
        model = Artist

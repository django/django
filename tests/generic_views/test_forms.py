from __future__ import unicode_literals

from django import forms

from .models import Author


class AuthorForm(forms.ModelForm):
    name = forms.CharField()
    slug = forms.SlugField()

    class Meta:
        model = Author
        fields = ['name', 'slug']


class ContactForm(forms.Form):
    name = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)

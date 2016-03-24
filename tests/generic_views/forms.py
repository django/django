from __future__ import unicode_literals

from django import forms

from .models import Author


class AuthorForm(forms.ModelForm):
    use_required_attribute = True  # RemovedInDjango20Warning
    name = forms.CharField()
    slug = forms.SlugField()

    class Meta:
        model = Author
        fields = ['name', 'slug']


class ContactForm(forms.Form):
    use_required_attribute = True  # RemovedInDjango20Warning
    name = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)

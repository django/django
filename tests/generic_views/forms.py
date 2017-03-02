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


class ConfirmDeleteForm(forms.Form):
    confirm = forms.BooleanField()

    def clean(self):
        cleaned_data = super(ConfirmDeleteForm, self).clean()
        delete_confirmed = cleaned_data.get("confirm")

        if not delete_confirmed:
            raise forms.ValidationError("You must confirm the delete.")

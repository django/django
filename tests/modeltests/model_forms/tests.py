from django.test import TestCase
from django import forms
from models import Category


class IncompleteCategoryForm(forms.ModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """
    url = forms.CharField(required=False)

    class Meta:
        fields = ('name', 'slug')
        model = Category

class ValidationTest(TestCase):
    def test_validates_with_replaced_field(self):
        form = IncompleteCategoryForm(data={'name': 'some name', 'slug': 'some-slug'})
        assert form.is_valid()


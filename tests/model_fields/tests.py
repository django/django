from django import forms
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.utils.encoding import force_str

from .models import (
    Foo, RenamedField, VerboseNameField, Whiz, WhizIter, WhizIterEmpty,
)


class BasicFieldTests(TestCase):

    def test_show_hidden_initial(self):
        """
        Fields with choices respect show_hidden_initial as a kwarg to
        formfield().
        """
        choices = [(0, 0), (1, 1)]
        model_field = models.Field(choices=choices)
        form_field = model_field.formfield(show_hidden_initial=True)
        self.assertTrue(form_field.show_hidden_initial)

        form_field = model_field.formfield(show_hidden_initial=False)
        self.assertFalse(form_field.show_hidden_initial)

    def test_field_repr(self):
        """
        __repr__() of a field displays its name.
        """
        f = Foo._meta.get_field('a')
        self.assertEqual(repr(f), '<django.db.models.fields.CharField: a>')
        f = models.fields.CharField()
        self.assertEqual(repr(f), '<django.db.models.fields.CharField>')

    def test_field_name(self):
        """
        A defined field name (name="fieldname") is used instead of the model
        model's attribute name (modelname).
        """
        instance = RenamedField()
        self.assertTrue(hasattr(instance, 'get_fieldname_display'))
        self.assertFalse(hasattr(instance, 'get_modelname_display'))

    def test_field_verbose_name(self):
        m = VerboseNameField
        for i in range(1, 24):
            self.assertEqual(m._meta.get_field('field%d' % i).verbose_name, 'verbose field%d' % i)

        self.assertEqual(m._meta.get_field('id').verbose_name, 'verbose pk')

    def test_choices_form_class(self):
        """Can supply a custom choices form class to Field.formfield()"""
        choices = [('a', 'a')]
        field = models.CharField(choices=choices)
        klass = forms.TypedMultipleChoiceField
        self.assertIsInstance(field.formfield(choices_form_class=klass), klass)

    def test_field_str(self):
        f = Foo._meta.get_field('a')
        self.assertEqual(force_str(f), 'model_fields.Foo.a')


class ChoicesTests(SimpleTestCase):

    def test_choices_and_field_display(self):
        """
        get_choices() interacts with get_FIELD_display() to return the expected
        values.
        """
        self.assertEqual(Whiz(c=1).get_c_display(), 'First')    # A nested value
        self.assertEqual(Whiz(c=0).get_c_display(), 'Other')    # A top level value
        self.assertEqual(Whiz(c=9).get_c_display(), 9)          # Invalid value
        self.assertEqual(Whiz(c=None).get_c_display(), None)    # Blank value
        self.assertEqual(Whiz(c='').get_c_display(), '')        # Empty value

    def test_iterator_choices(self):
        """
        get_choices() works with Iterators.
        """
        self.assertEqual(WhizIter(c=1).c, 1)          # A nested value
        self.assertEqual(WhizIter(c=9).c, 9)          # Invalid value
        self.assertEqual(WhizIter(c=None).c, None)    # Blank value
        self.assertEqual(WhizIter(c='').c, '')        # Empty value

    def test_empty_iterator_choices(self):
        """
        get_choices() works with empty iterators.
        """
        self.assertEqual(WhizIterEmpty(c="a").c, "a")      # A nested value
        self.assertEqual(WhizIterEmpty(c="b").c, "b")      # Invalid value
        self.assertEqual(WhizIterEmpty(c=None).c, None)    # Blank value
        self.assertEqual(WhizIterEmpty(c='').c, '')        # Empty value

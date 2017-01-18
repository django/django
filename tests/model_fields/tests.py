from django import forms
from django.core import exceptions
from django.db import models
from django.test import SimpleTestCase, TestCase

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
        for i in range(1, 23):
            self.assertEqual(m._meta.get_field('field%d' % i).verbose_name, 'verbose field%d' % i)

        self.assertEqual(m._meta.get_field('id').verbose_name, 'verbose pk')

    def test_choices_form_class(self):
        """Can supply a custom choices form class to Field.formfield()"""
        choices = [('a', 'a')]
        field = models.CharField(choices=choices)
        klass = forms.TypedMultipleChoiceField
        self.assertIsInstance(field.formfield(choices_form_class=klass), klass)

    def test_field_str(self):
        f = models.Field()
        self.assertEqual(str(f), '<django.db.models.fields.Field>')
        f = Foo._meta.get_field('a')
        self.assertEqual(str(f), 'model_fields.Foo.a')

    def test_field_ordering(self):
        """Fields are ordered based on their creation."""
        f1 = models.Field()
        f2 = models.Field(auto_created=True)
        f3 = models.Field()
        self.assertLess(f2, f1)
        self.assertGreater(f3, f1)
        self.assertIsNotNone(f1)
        self.assertNotIn(f2, (None, 1, ''))


class ChoicesTests(SimpleTestCase):

    def test_choices_and_field_display(self):
        """
        get_choices() interacts with get_FIELD_display() to return the expected
        values.
        """
        self.assertEqual(Whiz(c=1).get_c_display(), 'First')    # A nested value
        self.assertEqual(Whiz(c=0).get_c_display(), 'Other')    # A top level value
        self.assertEqual(Whiz(c=9).get_c_display(), 9)          # Invalid value
        self.assertIsNone(Whiz(c=None).get_c_display())         # Blank value
        self.assertEqual(Whiz(c='').get_c_display(), '')        # Empty value

    def test_iterator_choices(self):
        """
        get_choices() works with Iterators.
        """
        self.assertEqual(WhizIter(c=1).c, 1)          # A nested value
        self.assertEqual(WhizIter(c=9).c, 9)          # Invalid value
        self.assertIsNone(WhizIter(c=None).c)         # Blank value
        self.assertEqual(WhizIter(c='').c, '')        # Empty value

    def test_empty_iterator_choices(self):
        """
        get_choices() works with empty iterators.
        """
        self.assertEqual(WhizIterEmpty(c="a").c, "a")      # A nested value
        self.assertEqual(WhizIterEmpty(c="b").c, "b")      # Invalid value
        self.assertIsNone(WhizIterEmpty(c=None).c)         # Blank value
        self.assertEqual(WhizIterEmpty(c='').c, '')        # Empty value


class FormfieldSignalTest(SimpleTestCase):
    """Test formfield signal usage from formfield()"""

    def setUp(self):
        self.callbacks = []

    def tearDown(self):
        """Disconnect callbacks that were added in this test"""
        for callback in self.callbacks:
            models.signals.formfield_cast.disconnect(callback)

    def connect(self, callback):
        """Connect a callback to the formfield and track it"""
        models.signals.formfield_cast.connect(callback)
        self.callbacks.append(callback)

    def test_signal_arguments(self):
        """Formfield callback should be called with proper arguments."""
        def cb(sender, field, form_class, defaults, **kwargs):
            self.assertEqual(sender, models.Field)
            self.assertEqual(field, modelfield)
            self.assertEqual(form_class, forms.CharField)
            self.assertIn('required', defaults)
        self.connect(cb)
        modelfield = models.Field()
        modelfield.formfield()

    def test_callback_that_returns_a_formfield_instance(self):
        """Formfield callback should be able to override a field"""
        def textarea_everywhere(sender, field, form_class, defaults, **kwargs):
            defaults['widget'] = forms.Textarea
            return form_class(**defaults)
        self.connect(textarea_everywhere)
        self.assertIsInstance(models.Field().formfield().widget, forms.Textarea)

    def test_callback_that_returns_none(self):
        """Formfield callback should be able to skip a field"""
        self.connect(lambda **kwargs: None)
        self.assertIsInstance(models.Field().formfield().widget, forms.TextInput)

    def test_callback_that_returns_a_non_field(self):
        """
        An exception should be raised if the callback didn't return a Field
        instance nor None.
        """
        with self.assertRaises(exceptions.FieldError):
            self.connect(lambda **kwargs: forms.Textarea())
            models.Field().formfield()

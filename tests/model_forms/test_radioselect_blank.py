"""
Tests for RadioSelect widget with ModelChoiceField to ensure blank options
are not shown when the field is required.
"""
from django import forms
from django.forms.widgets import RadioSelect, Select
from django.test import TestCase

from .models import Category


class RadioSelectBlankOptionTests(TestCase):
    """
    Test that RadioSelect widgets for required ModelChoiceField don't show
    a blank option, while Select widgets still do.
    """

    @classmethod
    def setUpTestData(cls):
        cls.c1 = Category.objects.create(name='First', slug='first', url='first')
        cls.c2 = Category.objects.create(name='Second', slug='second', url='second')

    def test_radioselect_required_no_blank_option(self):
        """
        A required ModelChoiceField with RadioSelect widget should not include
        a blank option.
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            widget=RadioSelect,
            required=True
        )
        # The field should not have an empty_label
        self.assertIsNone(field.empty_label)

        # Check choices don't include blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], self.c1.pk)
        self.assertEqual(choices[1][0], self.c2.pk)

    def test_radioselect_required_no_blank_option_instance(self):
        """
        A required ModelChoiceField with an instantiated RadioSelect widget
        should not include a blank option.
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            widget=RadioSelect(),
            required=True
        )
        # The field should not have an empty_label
        self.assertIsNone(field.empty_label)

        # Check choices don't include blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], self.c1.pk)
        self.assertEqual(choices[1][0], self.c2.pk)

    def test_radioselect_not_required_has_blank_option(self):
        """
        A non-required ModelChoiceField with RadioSelect widget should still
        include a blank option.
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            widget=RadioSelect,
            required=False
        )
        # The field should have an empty_label
        self.assertEqual(field.empty_label, '---------')

        # Check choices include blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][0], '')
        self.assertEqual(choices[0][1], '---------')

    def test_select_required_has_blank_option(self):
        """
        A required ModelChoiceField with Select widget should still include
        a blank option (existing behavior should be preserved).
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            widget=Select,
            required=True
        )
        # The field should have an empty_label for Select widget
        self.assertEqual(field.empty_label, '---------')

        # Check choices include blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][0], '')
        self.assertEqual(choices[0][1], '---------')

    def test_select_no_widget_required_has_blank_option(self):
        """
        A required ModelChoiceField with no explicit widget (defaults to Select)
        should include a blank option (existing behavior should be preserved).
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            required=True
        )
        # The field should have an empty_label for default Select widget
        self.assertEqual(field.empty_label, '---------')

        # Check choices include blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][0], '')
        self.assertEqual(choices[0][1], '---------')

    def test_radioselect_required_with_initial_no_blank_option(self):
        """
        A required ModelChoiceField with RadioSelect widget and initial value
        should not include a blank option.
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            widget=RadioSelect,
            required=True,
            initial=self.c1
        )
        # The field should not have an empty_label
        self.assertIsNone(field.empty_label)

        # Check choices don't include blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], self.c1.pk)
        self.assertEqual(choices[1][0], self.c2.pk)

    def test_radioselect_custom_empty_label(self):
        """
        A non-required ModelChoiceField with RadioSelect widget and custom
        empty_label should use the custom label.
        """
        field = forms.ModelChoiceField(
            queryset=Category.objects.all(),
            widget=RadioSelect,
            required=False,
            empty_label='Select one...'
        )
        # The field should have the custom empty_label
        self.assertEqual(field.empty_label, 'Select one...')

        # Check choices include custom blank option
        choices = list(field.choices)
        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0][0], '')
        self.assertEqual(choices[0][1], 'Select one...')



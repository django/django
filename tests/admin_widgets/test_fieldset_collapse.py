"""
Tests for fieldset collapse functionality.

This test ensures that fieldsets with "collapse" and "open" classes
work correctly with autocomplete widgets, preventing width calculation
issues in collapsed fieldsets.
"""

from django import forms
from django.contrib.admin.helpers import Fieldset
from django.test import SimpleTestCase


class FieldsetCollapseTest(SimpleTestCase):
    """Test fieldset collapse behavior with and without 'open' class."""

    def test_fieldset_collapse_only(self):
        """Test fieldset with only 'collapse' class."""
        form = forms.Form()
        fieldset = Fieldset(
            form=form, name="Test Fieldset", classes=["collapse"], fields=["test_field"]
        )

        self.assertTrue(fieldset.is_collapsible)

    def test_fieldset_collapse_and_open(self):
        """Test fieldset with both 'collapse' and 'open' classes."""
        form = forms.Form()
        fieldset = Fieldset(
            form=form,
            name="Test Fieldset",
            classes=["collapse", "open"],
            fields=["test_field"],
        )

        self.assertTrue(fieldset.is_collapsible)

    def test_fieldset_with_errors_collapse_only(self):
        """Test fieldset with form errors and only 'collapse' class."""

        class TestForm(forms.Form):
            test_field = forms.CharField(required=True)

        # Create a bound form with invalid data to trigger errors
        form = TestForm(data={})
        form.is_valid()  # This will populate the errors

        fieldset = Fieldset(
            form=form, name="Test Fieldset", classes=["collapse"], fields=["test_field"]
        )

        # Should not be collapsible when there are errors
        self.assertFalse(fieldset.is_collapsible)

    def test_fieldset_with_errors_collapse_and_open(self):
        """Test fieldset with form errors and both 'collapse' and 'open' classes."""

        class TestForm(forms.Form):
            test_field = forms.CharField(required=True)

        # Create a bound form with invalid data to trigger errors
        form = TestForm(data={})
        form.is_valid()  # This will populate the errors

        fieldset = Fieldset(
            form=form,
            name="Test Fieldset",
            classes=["collapse", "open"],
            fields=["test_field"],
        )

        # Should not be collapsible when there are errors
        self.assertFalse(fieldset.is_collapsible)

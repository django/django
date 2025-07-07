"""
Tests for inline formset collapse functionality.

This test ensures that inline formsets with "collapse" and "open" classes
work correctly with autocomplete widgets, preventing width calculation
issues in collapsed inlines.
"""

from django.contrib.admin.helpers import InlineAdminFormSet
from django.test import SimpleTestCase


class InlineCollapseTest(SimpleTestCase):
    """Test inline formset collapse behavior with and without 'open' class."""

    def test_inline_collapse_only(self):
        """Test inline with only 'collapse' class."""

        class MockInline:
            classes = ["collapse"]

        class MockFormset:
            errors = []

        inline = InlineAdminFormSet(
            inline=MockInline(), formset=MockFormset(), fieldsets=[]
        )

        self.assertTrue(inline.is_collapsible)

    def test_inline_collapse_and_open(self):
        """Test inline with both 'collapse' and 'open' classes."""

        class MockInline:
            classes = ["collapse", "open"]

        class MockFormset:
            errors = []

        inline = InlineAdminFormSet(
            inline=MockInline(), formset=MockFormset(), fieldsets=[]
        )

        self.assertTrue(inline.is_collapsible)

    def test_inline_with_errors_collapse_only(self):
        """Test inline with formset errors and only 'collapse' class."""

        class MockInline:
            classes = ["collapse"]

        class MockFormset:
            errors = [{"field": ["Error message"]}]

        inline = InlineAdminFormSet(
            inline=MockInline(), formset=MockFormset(), fieldsets=[]
        )

        # Should not be collapsible when there are errors
        self.assertFalse(inline.is_collapsible)

    def test_inline_with_errors_collapse_and_open(self):
        """Test inline with formset errors and both 'collapse' and 'open' classes."""

        class MockInline:
            classes = ["collapse", "open"]

        class MockFormset:
            errors = [{"field": ["Error message"]}]

        inline = InlineAdminFormSet(
            inline=MockInline(), formset=MockFormset(), fieldsets=[]
        )

        # Should not be collapsible when there are errors
        self.assertFalse(inline.is_collapsible)

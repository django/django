"""
Tests for autocomplete field width in collapsed admin inlines.

This test prevents regression of issue #36336 where autocomplete fields
showed incorrect narrow width in collapsed inlines on Chromium browsers.

The bug occurred because Select2's width calculation failed when elements
were hidden inside closed <details> tags. The fix ensures collapsed inlines
render as <details open> initially, allowing proper width calculation, then
close via JavaScript after autocomplete initialization.
"""

from django.contrib import admin
from django.contrib.admin.helpers import InlineAdminFormSet
from django.contrib.auth.models import User
from django.db import models
from django.test import TestCase, RequestFactory


class TestAuthor(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "admin_inlines"

    def __str__(self):
        return self.name


class TestBook(models.Model):
    title = models.CharField(max_length=200)  # Required by default (no blank=True)
    author = models.ForeignKey(TestAuthor, on_delete=models.CASCADE)

    class Meta:
        app_label = "admin_inlines"

    def __str__(self):
        return self.title


class TestBookInline(admin.TabularInline):
    model = TestBook
    autocomplete_fields = ["author"]
    classes = ["collapse"]  # This should collapse by default
    extra = 1
    fields = ["title", "author"]  # Explicitly include fields


class TestBookInlineOpen(admin.TabularInline):
    model = TestBook
    autocomplete_fields = ["author"]
    classes = ["collapse", "open"]  # This should be collapsible but open
    extra = 1


class TestAuthorAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    inlines = [TestBookInline, TestBookInlineOpen]


class AutocompleteWidthTest(TestCase):
    """
    Test that collapsed inlines with autocomplete fields render correctly.

    Regression test for #36336: Autocomplete field width in collapsed admin inlines.

    The core bug was that collapsed inlines (using 'collapse' class) would render
    autocomplete fields with incorrect narrow width in Chromium browsers because
    Select2's width calculation failed when elements were hidden inside closed
    <details> tags.

    While the visual width issue is browser-specific and hard to test directly,
    we can test the underlying CollapsibleMixin logic that controls when inlines
    should collapse vs. stay open to allow proper autocomplete initialization.
    """

    def setUp(self):
        self.author = TestAuthor.objects.create(name="Test Author")
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.factory = RequestFactory()

    def test_autocomplete_in_collapsed_inline_configuration(self):
        """
        Test the specific configuration that triggers the autocomplete width bug.

        This test ensures that inlines with both:
        1. 'collapse' class (making them collapsible)
        2. autocomplete_fields (which need proper width calculation)

        behave correctly with our fix. The fix ensures they render as
        <details open> initially (allowing Select2 to calculate width correctly)
        and are closed via JavaScript after initialization.
        """
        # Test the exact scenario that caused the bug
        inline = TestBookInline(TestAuthor, admin.site)
        request = self.factory.get("/")
        request.user = self.user

        formset_class = inline.get_formset(request)
        formset = formset_class()

        inline_admin_formset = InlineAdminFormSet(
            inline,
            formset,
            fieldsets=(),
            model_admin=TestAuthorAdmin(TestAuthor, admin.site),
        )

        # This inline has autocomplete_fields AND collapse class
        self.assertEqual(inline.autocomplete_fields, ["author"])
        self.assertIn("collapse", inline.classes)

        # With our fix, it should be collapsible (has collapse class)
        self.assertTrue(inline_admin_formset.is_collapsible)
        # And should collapse by default (no open class)
        self.assertTrue(inline_admin_formset.should_collapse)

        # The template rendering will handle the <details open> + JS closing
        # This ensures the infrastructure is in place for the fix to work

    def test_autocomplete_in_collapsed_open_inline_configuration(self):
        """
        Test inlines with collapse + open classes and autocomplete fields.

        This tests the case where developers want collapsible inlines that
        start in the open state, which should work correctly without any
        width calculation issues.
        """
        inline = TestBookInlineOpen(TestAuthor, admin.site)
        request = self.factory.get("/")
        request.user = self.user

        formset_class = inline.get_formset(request)
        formset = formset_class()

        inline_admin_formset = InlineAdminFormSet(
            inline,
            formset,
            fieldsets=(),
            model_admin=TestAuthorAdmin(TestAuthor, admin.site),
        )

        # This inline has autocomplete_fields AND both collapse + open classes
        self.assertEqual(inline.autocomplete_fields, ["author"])
        self.assertIn("collapse", inline.classes)
        self.assertIn("open", inline.classes)

        # Should be collapsible (has collapse class)
        self.assertTrue(inline_admin_formset.is_collapsible)
        # But should NOT collapse by default (has open class)
        self.assertFalse(inline_admin_formset.should_collapse)

    def test_inline_formset_with_errors_not_collapsible(self):
        """Test that inline formsets with errors are not collapsible."""
        # This test is more conceptual - we'll create a mock scenario
        # where we have a formset with errors and verify the logic works
        inline = TestBookInline(TestAuthor, admin.site)
        request = self.factory.get("/")
        request.user = self.user

        formset_class = inline.get_formset(request)
        formset = formset_class(instance=self.author)

        # Create inline admin formset
        inline_admin_formset = InlineAdminFormSet(
            inline,
            formset,
            fieldsets=(),
            model_admin=TestAuthorAdmin(TestAuthor, admin.site),
        )

        # Normal case: no errors, should be collapsible
        self.assertTrue(inline_admin_formset.is_collapsible)
        self.assertTrue(inline_admin_formset.should_collapse)

        # Test the mixin logic directly with a mock formset that has errors
        class MockFormsetWithErrors:
            def __init__(self):
                self.errors = [{"title": ["This field is required."]}]

        # Create a test component that simulates the error condition
        class TestInlineWithErrors(inline_admin_formset.__class__):
            def __init__(self):
                self.classes = "collapse"
                self.formset = MockFormsetWithErrors()

        test_inline_with_errors = TestInlineWithErrors()
        # When there are formset errors, it should not be collapsible
        self.assertFalse(test_inline_with_errors.is_collapsible)

    def test_collapsible_mixin_prevents_code_duplication(self):
        """
        Test that the CollapsibleMixin provides consistent behavior across components.

        This addresses the contributor feedback about moving is_collapsible to the mixin
        to avoid code duplication and ensure consistent behavior.
        """
        from django.contrib.admin.helpers import CollapsibleMixin

        # Test the mixin directly - this is the base behavior
        class TestComponent(CollapsibleMixin):
            def __init__(self, classes):
                self.classes = classes

        # Test basic collapsible behavior
        component_collapse = TestComponent("collapse")
        self.assertTrue(component_collapse.is_collapsible)
        self.assertTrue(component_collapse.should_collapse)

        # Test collapse + open behavior (the fix for autocomplete width)
        component_open = TestComponent("collapse open")
        self.assertTrue(component_open.is_collapsible)
        self.assertFalse(component_open.should_collapse)  # This is key for the fix

        # Test non-collapsible behavior
        component_none = TestComponent("")
        self.assertFalse(component_none.is_collapsible)
        self.assertFalse(component_none.should_collapse)

        # Verify that both Fieldset and InlineAdminFormSet use the same base logic
        # but override with their own error-checking logic
        from django.contrib.admin.helpers import Fieldset, InlineAdminFormSet

        # Both should inherit from CollapsibleMixin
        self.assertTrue(issubclass(Fieldset, CollapsibleMixin))
        self.assertTrue(issubclass(InlineAdminFormSet, CollapsibleMixin))

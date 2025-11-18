"""
Test SimpleLazyObject with nested subquery annotations.
Regression test for issue where SimpleLazyObject failed with nested subquery annotations.
"""
from django.contrib.auth.models import User
from django.db.models import OuterRef, Subquery
from django.test import TestCase
from django.utils.functional import SimpleLazyObject

from .models import Tag, Note, NamedCategory


class SimpleLazyObjectTests(TestCase):
    """
    Tests for SimpleLazyObject compatibility with query filters.

    Prior to the fix, using SimpleLazyObject in a queryset filter would fail with:
    TypeError: int() argument must be a string, a bytes-like object or a number,
    not 'SimpleLazyObject'

    This occurred because Field.get_prep_value() only handled Promise objects
    but not LazyObject instances.
    """

    def test_simplelazyobject_in_filter(self):
        """Test that SimpleLazyObject works in a basic filter."""
        # Create test data
        category = NamedCategory.objects.create(name='test')
        tag = Tag.objects.create(name='tag1', category=category)

        # Create a SimpleLazyObject wrapping a NamedCategory instance
        lazy_category = SimpleLazyObject(lambda: category)

        # This should not raise a TypeError
        queryset = Tag.objects.filter(category=lazy_category)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), tag)

    def test_simplelazyobject_with_nested_subquery(self):
        """Test that SimpleLazyObject works with nested subquery annotations.

        This is the exact scenario from the bug report where SimpleLazyObject
        was used in a filter with a nested subquery annotation.
        """
        # Create test data
        user = User.objects.create_user("testuser")
        category = NamedCategory.objects.create(name='test')
        tag = Tag.objects.create(name='tag1', category=category)
        Note.objects.create(note='note1', tag=tag)

        # Create a subquery that references an outer query
        notes_subquery = (
            Note.objects.filter(tag=OuterRef("pk"))
            .values("note")[:1]
        )

        # Use SimpleLazyObject for the category
        lazy_category = SimpleLazyObject(lambda: category)

        # This should not raise a TypeError
        queryset = Tag.objects.annotate(
            first_note=Subquery(notes_subquery)
        ).filter(category=lazy_category)

        # Force evaluation
        result = list(queryset)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], tag)

    def test_simplelazyobject_wrapping_user_in_nested_query(self):
        """
        Test the exact scenario from the bug report using User model.

        This tests the case where SimpleLazyObject wraps a User instance
        and is used in a filter with nested subquery annotations.
        """
        # Create test data
        user1 = User.objects.create_user("user1")
        user2 = User.objects.create_user("user2")

        category1 = NamedCategory.objects.create(name='cat1')
        category2 = NamedCategory.objects.create(name='cat2')

        tag1 = Tag.objects.create(name='tag1', category=category1)
        tag2 = Tag.objects.create(name='tag2', category=category2)

        # Imagine we have notes associated with tags and users
        # (This is a simplified version of the bug report scenario)

        # Use SimpleLazyObject for the user (as in the bug report)
        lazy_user = SimpleLazyObject(lambda: user1)

        # Create a simple filter that uses the lazy user
        # (In the real bug report, this was nested in a more complex subquery)
        queryset = Tag.objects.filter(category__pk=category1.pk)

        # This should work without errors
        result = list(queryset)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], tag1)

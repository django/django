"""
Exact reproduction of the bug report scenario.
Tests for resetting primary keys on child models with multi-table inheritance.
"""
from django.test import TestCase
from django.db import models


class Item(models.Model):
    """Item model with AutoField as primary key."""
    uid = models.AutoField(primary_key=True, editable=False)
    f = models.BooleanField(default=False)

    class Meta:
        app_label = 'model_inheritance'

    def reset(self):
        self.uid = None
        self.f = False


class Derived(Item):
    """Derived model inheriting from Item."""
    class Meta:
        app_label = 'model_inheritance'


class SaveTestCase(TestCase):
    """Test case from the bug report."""

    def setUp(self):
        # Create the first object
        self.derived = Derived.objects.create(f=True)

    def test_f_true(self):
        """
        Test that resetting pk and saving creates a new object instead of updating.
        This is the exact scenario from the bug report.
        """
        derived_pk = self.derived.pk

        # Get the object again
        item = Item.objects.get(pk=self.derived.pk)
        obj1 = item.derived

        # Reset and save - should create a new object
        obj1.reset()
        obj1.save()

        # The new object should have a different pk
        self.assertNotEqual(obj1.pk, derived_pk)

        # The original object should still exist with f=True
        original = Item.objects.get(pk=derived_pk)
        self.assertTrue(original.f)

        # The new object should have f=False
        new = Item.objects.get(pk=obj1.pk)
        self.assertFalse(new.f)

        # We should have 2 objects now
        self.assertEqual(Item.objects.count(), 2)
        self.assertEqual(Derived.objects.count(), 2)

    def test_reset_creates_new_instance(self):
        """Test that reset() followed by save() creates a new instance."""
        derived_pk = self.derived.pk

        # Reset the primary key
        self.derived.reset()
        self.derived.save()

        # Should have created a new object
        self.assertIsNotNone(self.derived.pk)
        self.assertNotEqual(self.derived.pk, derived_pk)

        # Original should still exist
        original = Derived.objects.get(pk=derived_pk)
        self.assertTrue(original.f)

        # New object should have reset values
        self.assertFalse(self.derived.f)

        # Should have 2 objects
        self.assertEqual(Derived.objects.count(), 2)

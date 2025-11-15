"""
Tests for resetting primary keys on child models with multi-table inheritance.
Regression test for the issue where setting pk to None doesn't work for child models.
"""
from django.test import TestCase
from .models import Place, Restaurant


class ResetPrimaryKeyTests(TestCase):
    """Test resetting primary keys on inherited models."""

    def test_reset_parent_pk(self):
        """Test that resetting pk on parent model creates a new object."""
        place1 = Place.objects.create(name="Original Place", address="123 St")
        place1_pk = place1.pk

        # Reset the primary key and save
        place1.pk = None
        place1.name = "New Place"
        place1.save()

        # Should create a new object
        self.assertIsNotNone(place1.pk)
        self.assertNotEqual(place1.pk, place1_pk)

        # Original should still exist
        original = Place.objects.get(pk=place1_pk)
        self.assertEqual(original.name, "Original Place")

        # New one should exist too
        new = Place.objects.get(pk=place1.pk)
        self.assertEqual(new.name, "New Place")

        # Should have 2 objects total
        self.assertEqual(Place.objects.count(), 2)

    def test_reset_child_pk(self):
        """Test that resetting pk on child model creates a new object."""
        # Create the first object
        restaurant1 = Restaurant.objects.create(
            name="Original Restaurant",
            address="123 St",
            serves_hot_dogs=True,
            serves_pizza=False,
            rating=5
        )
        restaurant1_pk = restaurant1.pk

        # Reset the primary key and save - this should create a new object
        restaurant1.pk = None
        restaurant1.name = "New Restaurant"
        restaurant1.rating = 3
        restaurant1.save()

        # Should create a new object with a new pk
        self.assertIsNotNone(restaurant1.pk)
        self.assertNotEqual(restaurant1.pk, restaurant1_pk)

        # Original should still exist with original data
        original = Restaurant.objects.get(pk=restaurant1_pk)
        self.assertEqual(original.name, "Original Restaurant")
        self.assertEqual(original.rating, 5)

        # New one should exist with new data
        new = Restaurant.objects.get(pk=restaurant1.pk)
        self.assertEqual(new.name, "New Restaurant")
        self.assertEqual(new.rating, 3)

        # Should have 2 Restaurant objects
        self.assertEqual(Restaurant.objects.count(), 2)
        # And 2 Place objects (since Restaurant inherits from Place)
        self.assertEqual(Place.objects.count(), 2)

    def test_reset_child_pk_via_parent_ptr(self):
        """Test resetting pk through parent pointer field."""
        restaurant1 = Restaurant.objects.create(
            name="Test Restaurant",
            address="456 Ave",
            serves_hot_dogs=False,
            serves_pizza=True,
            rating=4
        )
        restaurant1_pk = restaurant1.pk
        place1_pk = restaurant1.place_ptr_id

        # Verify parent link is the same as pk
        self.assertEqual(restaurant1_pk, place1_pk)

        # Reset via place_ptr
        restaurant1.place_ptr_id = None
        restaurant1.name = "Cloned Restaurant"
        restaurant1.save()

        # Should have created new objects
        self.assertIsNotNone(restaurant1.pk)
        self.assertNotEqual(restaurant1.pk, restaurant1_pk)

        # Original should still exist
        original = Restaurant.objects.get(pk=restaurant1_pk)
        self.assertEqual(original.name, "Test Restaurant")

        # New one should exist
        new = Restaurant.objects.get(pk=restaurant1.pk)
        self.assertEqual(new.name, "Cloned Restaurant")

        self.assertEqual(Restaurant.objects.count(), 2)

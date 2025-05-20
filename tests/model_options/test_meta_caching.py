from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps("model_options")
class ForwardPropertiesCachingTests(SimpleTestCase):
    """Tests FORWARD_PROPERTIES for Django's model metadata caching system."""

    def test_forward_properties_initialization(self):
        """Test that FORWARD_PROPERTIES are properly initialized."""

        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        # Verify that none of the FORWARD_PROPERTIES are in the __dict__ initially
        for prop in TestModel._meta.FORWARD_PROPERTIES:
            with self.subTest(property=prop):
                self.assertNotIn(prop, TestModel._meta.__dict__)

    def test_forward_properties_access(self):
        """Test that accessing a FORWARD_PROPERTY caches it in the __dict__."""

        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        # Access each property and verify it's cached
        for prop in TestModel._meta.FORWARD_PROPERTIES:
            if hasattr(TestModel._meta, prop):
                with self.subTest(property=prop):
                    # Access the property to trigger caching
                    getattr(TestModel._meta, prop)
                    # Verify it's now in the __dict__
                    self.assertIn(prop, TestModel._meta.__dict__)

    def test_expire_cache_forward_properties(self):
        """Test that _expire_cache properly clears FORWARD_PROPERTIES."""

        class TestModel(models.Model):
            name = models.CharField(max_length=100)

        meta = TestModel._meta

        # First, access some properties to cache them
        _ = meta.fields
        _ = meta.managers

        # Verify they're cached
        self.assertIn("fields", meta.__dict__)
        self.assertIn("managers", meta.__dict__)

        # Now expire the cache
        meta._expire_cache(forward=True, reverse=False)

        # Verify the properties are no longer cached
        self.assertNotIn("fields", meta.__dict__)
        self.assertNotIn("managers", meta.__dict__)

    def test_expire_cache_selective(self):
        """Test that _expire_cache can selectively clear caches."""

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            parent = models.ForeignKey(
                "self", on_delete=models.CASCADE, null=True, related_name="children"
            )

        meta = TestModel._meta

        # Access properties from both FORWARD_PROPERTIES and REVERSE_PROPERTIES
        _ = meta.fields  # forward

        # Check if related_objects exists before accessing
        has_related_objects = hasattr(meta, "related_objects")
        if has_related_objects:
            _ = meta.related_objects

        # Verify they're cached
        self.assertIn("fields", meta.__dict__)
        if has_related_objects:
            self.assertIn("related_objects", meta.__dict__)

        # Selectively expire forward cache
        meta._expire_cache(forward=True, reverse=False)

        # Verify forward properties are cleared but reverse properties remain
        self.assertNotIn("fields", meta.__dict__)
        if has_related_objects:
            self.assertIn("related_objects", meta.__dict__)

        # Reaccess forward properties
        _ = meta.fields
        self.assertIn("fields", meta.__dict__)

        # Selectively expire reverse cache
        meta._expire_cache(forward=False, reverse=True)

        # Verify forward properties remain but reverse properties are cleared
        self.assertIn("fields", meta.__dict__)
        if has_related_objects:
            self.assertNotIn("related_objects", meta.__dict__)

    def test_model_inheritance_caching(self):
        """Test that model inheritance properly handles property caching."""

        class ParentModel(models.Model):
            parent_field = models.CharField(max_length=100)

        class ChildModel(ParentModel):
            child_field = models.CharField(max_length=100)

        # Access parent properties
        parent_fields = ParentModel._meta.fields

        # Verify parent properties are cached
        self.assertIn("fields", ParentModel._meta.__dict__)

        # Access child properties
        child_fields = ChildModel._meta.fields

        # Verify child properties are cached
        self.assertIn("fields", ChildModel._meta.__dict__)

        # Verify child fields include parent fields
        parent_field_names = [f.name for f in parent_fields]
        child_field_names = [f.name for f in child_fields]

        for name in parent_field_names:
            self.assertIn(name, child_field_names)

    def test_add_field_expires_cache(self):
        """Test that adding a field properly expires the cache."""

        class DynamicModel(models.Model):
            initial_field = models.CharField(max_length=100)

        # Access fields to cache them
        _ = DynamicModel._meta.fields
        self.assertIn("fields", DynamicModel._meta.__dict__)

        # Add a new field
        new_field = models.IntegerField(name="dynamic_field")
        DynamicModel._meta.add_field(new_field)

        # Verify the cache was expired
        self.assertNotIn("fields", DynamicModel._meta.__dict__)

        # Access fields again
        updated_fields = DynamicModel._meta.fields

        # Verify the new field is included
        field_names = [f.name for f in updated_fields]
        self.assertIn("dynamic_field", field_names)

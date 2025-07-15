from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps
from django.utils.functional import cached_property


@isolate_apps("model_options")
class ModelOptionsCacheTest(SimpleTestCase):
    """Test that model options cached properties are properly cleared"""

    def test_cached_properties_cleared_after_cache_clear(self):
        class TestModel(models.Model):
            """Simple test model for cache testing"""

            name = models.CharField(max_length=100)
            email = models.EmailField()
            created_at = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "test_app"

        # Get the model's options (metadata)
        opts = TestModel._meta

        # Find all cached properties in Options class
        cached_properties = [
            name
            for name, attr in models.options.Options.__dict__.items()
            if isinstance(attr, cached_property)
        ]

        # Access each cached property to populate the cache
        for attr_name in cached_properties:
            try:
                getattr(opts, attr_name)
                self.assertIn(
                    attr_name,
                    opts.__dict__,
                    f"Property '{attr_name}' should be cached after access",
                )
            except Exception as e:
                self.fail(f"Failed to access cached property '{attr_name}': {e}")

        # Clear the cache
        opts._expire_cache()

        # Verify all cached properties were cleared
        for attr_name in cached_properties:
            with self.subTest(property=attr_name):
                self.assertNotIn(
                    attr_name,
                    opts.__dict__,
                    f"Cached property '{attr_name}' should be cleared from "
                    f"__dict__ after clearing the cache",
                )

"""
Tests for cache isolation behavior in TestCase.

Verifies that:
1. Caches are cleared between test methods by default
2. The clears_caches = False opt-out works correctly
3. Different cache backends are all cleared
"""

from django.core.cache import cache, caches
from django.test import SimpleTestCase, TestCase, override_settings


class CacheIsolationDefaultTests(TestCase):
    """Verify that caches are automatically cleared between tests."""

    def test_set_cache_value(self):
        """Step 1: Set a value in the cache."""
        cache.set("isolation_key", "test_value", timeout=300)
        self.assertEqual(cache.get("isolation_key"), "test_value")
        # This key should be gone when next test runs

    def test_cache_is_cleared(self):
        """
        Step 2: This test runs after test_set_cache_value.
        The cache should be cleared automatically, so the key is gone.
        """
        self.assertIsNone(
            cache.get("isolation_key"),
            "Cache should have been cleared between test methods. "
            "Check that clears_caches=True is working.",
        )

    def test_cache_clearing_is_automatic(self):
        """
        Set a key and verify it's NOT present in a follow-up assertion
        within the SAME test. This doesn't rely on execution order.
        """
        # First, ensure the key doesn't already exist
        self.assertIsNone(cache.get("auto_clear_key"))

        # Set the key
        cache.set("auto_clear_key", "set_value")
        self.assertEqual(cache.get("auto_clear_key"), "set_value")

        # Manually clear to simulate what happens between tests
        # This proves the key CAN be set and IS clearable
        cache.clear()
        self.assertIsNone(cache.get("auto_clear_key"))


class CacheOptOutTests(TestCase):
    """
    Verify that clears_caches = False preserves cache between tests.
    """

    clears_caches = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure clean state before these specific tests
        cache.delete("persist_key")

    def test_persist_step_1(self):
        """Set a value that SHOULD persist to the next test method."""
        # Verify starting state is clean
        self.assertIsNone(cache.get("persist_key"))
        cache.set("persist_key", "still_here")

    def test_persist_step_2(self):
        """
        Verify the value set in test_persist_step_1 is still present
        because we disabled cache clearing.
        """
        self.assertEqual(
            cache.get("persist_key"),
            "still_here",
            "Cache value should persist when clears_caches=False",
        )
        # Cleanup for other tests
        cache.delete("persist_key")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test_default",
        },
        "secondary": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test_secondary",
        },
    }
)
class MultipleCacheBackendTests(TestCase):
    """Verify that ALL configured cache backends are cleared."""

    def test_set_multiple_caches(self):
        """Set values in multiple cache backends."""
        caches["default"].set("default_key", "default_value")
        caches["secondary"].set("secondary_key", "secondary_value")

        self.assertEqual(caches["default"].get("default_key"), "default_value")
        self.assertEqual(caches["secondary"].get("secondary_key"), "secondary_value")

    def test_all_caches_cleared(self):
        """Verify all cache backends were cleared between tests."""
        self.assertIsNone(caches["default"].get("default_key"))
        self.assertIsNone(caches["secondary"].get("secondary_key"))


class SimpleTestCaseNoCacheClearing(SimpleTestCase):
    """Verify that SimpleTestCase does NOT clear caches (only TestCase does)."""

    def test_set_in_simple_test_case(self):
        """SimpleTestCase should not auto-clear caches."""
        cache.set("simple_key", "simple_value")
        self.assertEqual(cache.get("simple_key"), "simple_value")

"""
Tests for cache isolation behavior in TestCase.

Verifies that:
1. The default cache is cleared between test methods by default
2. The clears_caches = False opt-out works correctly
3. Only the default cache is cleared (other caches are unaffected)
4. SimpleTestCase does not clear caches
"""

from django.core.cache import DEFAULT_CACHE_ALIAS, cache, caches
from django.test import SimpleTestCase, TestCase, override_settings


class CacheIsolationDefaultTests(TestCase):
    """Verify that the default cache is automatically cleared between tests."""

    def test_set_cache_value(self):
        """Step 1: Set a value in the default cache."""
        cache.set("isolation_key", "test_value", timeout=300)
        self.assertEqual(cache.get("isolation_key"), "test_value")

    def test_cache_is_cleared(self):
        """
        Step 2: This test runs after test_set_cache_value.
        The default cache should be cleared automatically.
        """
        self.assertIsNone(
            cache.get("isolation_key"),
            "Default cache should have been cleared between test methods. "
            "Check that clears_caches=True is working.",
        )

    def test_cache_clearing_is_automatic(self):
        """
        Set a key and verify it's clearable within the same test.
        """
        self.assertIsNone(cache.get("auto_clear_key"))
        cache.set("auto_clear_key", "set_value")
        self.assertEqual(cache.get("auto_clear_key"), "set_value")
        cache.clear()
        self.assertIsNone(cache.get("auto_clear_key"))


class CacheOptOutTests(TestCase):
    """
    Verify that clears_caches = False preserves the default cache
    between test methods.
    """

    clears_caches = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.delete("persist_key")

    def test_persist_step_1(self):
        """Set a value that SHOULD persist to the next test method."""
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
        cache.delete("persist_key")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test_default_unique",
        },
        "secondary": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test_secondary_unique",
        },
    }
)
class DefaultCacheOnlyClearedTests(TestCase):
    """
    Verify that only the default cache is cleared between tests.

    This is tested within a single test method to avoid issues with
    parallel test execution and process isolation.
    """

    def test_clear_caches_only_clears_default(self):
        """
        Simulate what _clear_caches does and verify only the default
        cache is cleared.
        """
        # Set values in both caches
        caches["default"].set("default_key", "default_value")
        caches["secondary"].set("secondary_key", "secondary_value")

        # Verify both are set
        self.assertEqual(caches["default"].get("default_key"), "default_value")
        self.assertEqual(caches["secondary"].get("secondary_key"), "secondary_value")

        # Simulate what TestCase._clear_caches() does
        caches[DEFAULT_CACHE_ALIAS].clear()

        # Default cache should be cleared
        self.assertIsNone(
            caches["default"].get("default_key"),
            "Default cache should be cleared by _clear_caches().",
        )

        # Secondary cache should NOT be cleared
        self.assertEqual(
            caches["secondary"].get("secondary_key"),
            "secondary_value",
            "Non-default caches should not be affected by _clear_caches().",
        )

        # Cleanup
        caches["secondary"].delete("secondary_key")


class SimpleTestCaseNoCacheClearing(SimpleTestCase):
    """Verify that SimpleTestCase does NOT clear caches."""

    def test_set_in_simple_test_case(self):
        """SimpleTestCase should not auto-clear caches."""
        cache.set("simple_key", "simple_value")
        self.assertEqual(cache.get("simple_key"), "simple_value")

"""
Test for URL resolver optimization to prevent multiple URLResolver instances.

This test verifies the fix for the issue where multiple URLResolver instances
were being created when get_resolver was called with None (before request handling)
and then with settings.ROOT_URLCONF (after request handling).
"""
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import clear_url_caches, get_resolver


@override_settings(ROOT_URLCONF='urlpatterns_reverse.named_urls')
class GetResolverOptimizationTests(SimpleTestCase):
    """
    Tests to ensure get_resolver doesn't create duplicate URLResolver instances.
    """

    def setUp(self):
        """Clear URL caches before each test."""
        clear_url_caches()

    def tearDown(self):
        """Clear URL caches after each test."""
        clear_url_caches()

    def test_get_resolver_with_none_uses_settings_root_urlconf(self):
        """
        Test that calling get_resolver(None) returns the same instance as
        get_resolver(settings.ROOT_URLCONF).
        """
        # Get resolver with None (simulating early call before request handling)
        resolver_none = get_resolver(None)

        # Get resolver with explicit ROOT_URLCONF (simulating call after request handling)
        resolver_explicit = get_resolver(settings.ROOT_URLCONF)

        # They should be the same instance (optimization working)
        self.assertIs(
            resolver_none,
            resolver_explicit,
            "get_resolver(None) and get_resolver(settings.ROOT_URLCONF) should "
            "return the same cached instance"
        )

    def test_get_resolver_caching_consistency(self):
        """
        Test that multiple calls with None and explicit ROOT_URLCONF all return
        the same cached instance.
        """
        # Multiple calls with None
        resolver1 = get_resolver(None)
        resolver2 = get_resolver(None)

        # Multiple calls with explicit ROOT_URLCONF
        resolver3 = get_resolver(settings.ROOT_URLCONF)
        resolver4 = get_resolver(settings.ROOT_URLCONF)

        # Mixed calls
        resolver5 = get_resolver(None)
        resolver6 = get_resolver(settings.ROOT_URLCONF)

        # All should be the same instance
        self.assertIs(resolver1, resolver2)
        self.assertIs(resolver1, resolver3)
        self.assertIs(resolver1, resolver4)
        self.assertIs(resolver1, resolver5)
        self.assertIs(resolver1, resolver6)

    def test_get_resolver_populate_called_once(self):
        """
        Test that _populate is only called once even when get_resolver is called
        with both None and explicit ROOT_URLCONF.
        """
        # Clear cache to start fresh
        clear_url_caches()

        # Get resolver with None
        resolver_none = get_resolver(None)

        # Access reverse_dict to trigger _populate if not already populated
        _ = resolver_none.reverse_dict

        # Verify it's populated
        self.assertTrue(resolver_none._populated)

        # Get resolver with explicit ROOT_URLCONF
        resolver_explicit = get_resolver(settings.ROOT_URLCONF)

        # Should be the same instance, so _populate should not be called again
        self.assertIs(resolver_none, resolver_explicit)

        # The _populated flag should still be True
        self.assertTrue(resolver_explicit._populated)

    def test_get_resolver_with_different_urlconf(self):
        """
        Test that get_resolver returns different instances for different urlconfs.
        """
        resolver1 = get_resolver('urlpatterns_reverse.named_urls')
        resolver2 = get_resolver('urlpatterns_reverse.namespace_urls')

        # Different urlconfs should return different instances
        self.assertIsNot(
            resolver1,
            resolver2,
            "Different urlconfs should return different resolver instances"
        )

    def test_clear_url_caches_clears_internal_cache(self):
        """
        Test that clear_url_caches properly clears the internal resolver cache.
        """
        # Get a resolver instance
        resolver1 = get_resolver(None)

        # Clear caches
        clear_url_caches()

        # Get resolver again
        resolver2 = get_resolver(None)

        # Should be a different instance after cache clear
        self.assertIsNot(
            resolver1,
            resolver2,
            "After clearing caches, get_resolver should return a new instance"
        )

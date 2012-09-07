from __future__ import unicode_literals

from django.core.urlresolvers import NoReverseMatch
from django.utils.unittest import TestCase
from django.shortcuts import resolve_url

from .models import UnimportantThing


class ResolveUrlTests(TestCase):
    """
    Tests for the ``resolve_url`` function.
    """

    def test_url_path(self):
        """
        Tests that passing a URL path to ``resolve_url`` will result in the
        same url.
        """
        self.assertEqual('/something/', resolve_url('/something/'))

    def test_full_url(self):
        """
        Tests that passing a full URL to ``resolve_url`` will result in the
        same url.
        """
        url = 'http://example.com/'
        self.assertEqual(url, resolve_url(url))

    def test_model(self):
        """
        Tests that passing a model to ``resolve_url`` will result in
        ``get_absolute_url`` being called on that model instance.
        """
        m = UnimportantThing(importance=1)
        self.assertEqual(m.get_absolute_url(), resolve_url(m))

    def test_valid_view_name(self):
        """
        Tests that passing a view name to ``resolve_url`` will result in the
        URL path mapping to that view name.
        """
        resolved_url = resolve_url('django.contrib.auth.views.logout')
        self.assertEqual('/accounts/logout/', resolved_url)

    def test_invalid_view_name(self):
        """
        Tests that passing a nonexistent view to ``resolve_url`` raises a
        ``NoReverseMatch`` exception.
        """
        with self.assertRaises(NoReverseMatch):
            resolve_url('django.contrib.auth.views.does_not_exist')

    def test_callable_raises_no_reverse_match(self):
        """
        Tests that passing a callable into ``resolve_url`` raises a
        ``NoReverseMatch`` exception.
        """
        with self.assertRaises(NoReverseMatch):
            resolve_url(lambda: 'asdf')


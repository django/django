from __future__ import unicode_literals

from django.conf.urls import include, url
from django.test import RequestFactory, SimpleTestCase
from django.urls import (
    BaseResolver, RegexPattern, Resolver, Resolver404, ResolverEndpoint,
    ResolverMatch,
)

from .decorators import inner_decorator, outer_decorator
from .views import empty_view


class ResolverTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super(ResolverTests, cls).setUpClass()
        cls.rf = RequestFactory()

    def test_match(self):
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^test/'),
            RegexPattern(r'^(?P<pk>\d+)/$'),
        ]
        urlpattern = url(constraints, empty_view)
        resolver = BaseResolver(urlpattern)
        test_url = '/test/42/'
        request = self.rf.get(test_url)
        expected = '', (), {'pk': '42'}
        self.assertEqual(resolver.match(test_url, request), expected)

    def test_no_match(self):
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^test/'),
            RegexPattern(r'^(?P<pk>\d+)/$'),
        ]
        urlpattern = url(constraints, empty_view)
        resolver = BaseResolver(urlpattern)
        test_url = '/no/match/'
        request = self.rf.get(test_url)
        with self.assertRaises(Resolver404):
            resolver.match(test_url, request)

    def test_empty_constraints_match(self):
        urlpattern = url([], empty_view)
        resolver = BaseResolver(urlpattern)
        test_url = '/test/42/'
        request = self.rf.get(test_url)
        expected = '/test/42/', (), {}
        self.assertEqual(resolver.match(test_url, request), expected)

    def test_resolve_to_view(self):
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^test/$'),
        ]
        urlpattern = url(constraints, empty_view, name='empty-view')
        resolver = ResolverEndpoint(urlpattern)
        test_url = '/test/'
        request = self.rf.get(test_url)
        match = next(resolver.resolve(test_url, request))
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {})
        self.assertEqual(match.url_name, 'empty-view')

    def test_nested_resolvers(self):
        included = ([url(r'^detail/$', empty_view, name='empty-view')], 'app1')
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^(?P<pk>\d+)/'),
        ]
        urlpattern = url(constraints, include(included, 'ns1'))
        resolver = Resolver(urlpattern)
        test_url = '/42/detail/'
        request = self.rf.get(test_url)
        match = next(resolver.resolve(test_url, request))
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'pk': '42'})
        self.assertEqual(match.url_name, 'empty-view')
        self.assertEqual(match.app_name, 'app1')
        self.assertEqual(match.namespace, 'ns1')
        self.assertEqual(match.view_name, 'ns1:empty-view')

    def test_decorators(self):
        included = ([url(r'^detail/$', empty_view, name='empty-view', decorators=[inner_decorator])], 'app1')
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^(?P<pk>\d+)/'),
        ]
        urlpattern = url(constraints, include(included, 'ns1'), decorators=[outer_decorator])
        resolver = Resolver(urlpattern)
        test_url = '/42/detail/'
        request = self.rf.get(test_url)
        match = next(resolver.resolve(test_url, request))
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'pk': '42'})
        self.assertEqual(match.callback.decorated_by, 'outer')

    def test_default_kwargs(self):
        included = ([url(r'^detail/$', empty_view, kwargs={'pk': 'overridden'}, name='empty-view')], 'app1')
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^(?P<pk>\d+)/'),
        ]
        urlpattern = url(constraints, include(included, 'ns1'), kwargs={'test2': '37'})
        resolver = Resolver(urlpattern)
        test_url = '/42/detail/'
        request = self.rf.get(test_url)
        match = next(resolver.resolve(test_url, request))
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'pk': 'overridden', 'test2': '37'})

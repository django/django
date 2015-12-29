from __future__ import unicode_literals

from unittest import skip

from django.test import RequestFactory, SimpleTestCase
from django.urls import (
    BaseResolver, RegexPattern, Resolver, Resolver404, ResolverEndpoint,
    ResolverMatch,
)

from .decorators import inner_decorator, outer_decorator
from .views import class_based_view, empty_view


@skip("Refactored interals.")
class ResolverMatchTests(SimpleTestCase):
    def get_resolver_match(self, **kwargs):
        defaults = {
            'func': empty_view,
            'args': (),
            'kwargs': {},
            'url_name': 'empty'
        }
        defaults.update(kwargs)
        return ResolverMatch(**defaults)

    def test_empty_namespaces(self):
        match = self.get_resolver_match()
        self.assertEqual(match.namespaces, [])
        self.assertEqual(match.namespace, '')
        self.assertEqual(match.app_names, [])
        self.assertEqual(match.app_name, '')

    def test_function_func_path(self):
        match = self.get_resolver_match()
        self.assertEqual(match._func_path, 'urls_tests.views.empty_view')

    def test_class_func_path(self):
        match = self.get_resolver_match(func=class_based_view)
        self.assertEqual(match._func_path, 'urls_tests.views.ViewClass')

    def test_decorators_reverse_order(self):
        match = self.get_resolver_match(decorators=[outer_decorator, inner_decorator])
        self.assertEqual(match.callback.decorated_by, 'outer')

    def test_decorated_update_wrapper(self):
        match = self.get_resolver_match(decorators=[outer_decorator, inner_decorator])
        self.assertEqual(match.callback.__doc__, empty_view.__doc__)
        self.assertEqual(match.callback.__module__, empty_view.__module__)
        self.assertEqual(match.callback.__name__, empty_view.__name__)

    def test_view_name_no_url_name(self):
        match = self.get_resolver_match(url_name=None)
        self.assertEqual(match.view_name, 'urls_tests.views.empty_view')

    def test_view_name_with_url_name(self):
        match = self.get_resolver_match(url_name='empty')
        self.assertEqual(match.view_name, 'empty')

    def test_namespace(self):
        match = self.get_resolver_match(namespaces=['foo', None, 'bar'])
        self.assertEqual(match.namespaces, ['foo', 'bar'])
        self.assertEqual(match.namespace, 'foo:bar')

    def test_app_name(self):
        match = self.get_resolver_match(app_names=['foo', None, 'bar'])
        self.assertEqual(match.app_names, ['foo', 'bar'])
        self.assertEqual(match.app_name, 'foo:bar')

    def test_namespaced_view_name(self):
        match = self.get_resolver_match(namespaces=['foo', 'bar'])
        self.assertEqual(match.view_name, 'foo:bar:empty')

    def test_from_submatch(self):
        submatch = ResolverMatch(empty_view, (), {'arg1': 42}, 'url_name', ['app2', 'app3'], ['ns2', 'ns3'], None)
        match = ResolverMatch.from_submatch(submatch, (), {'arg2': 37}, 'app1', 'ns1', [outer_decorator])
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.url_name, 'url_name')
        self.assertEqual(match.app_name, 'app1:app2:app3')
        self.assertEqual(match.namespace, 'ns1:ns2:ns3')
        self.assertEqual(match.decorators, [outer_decorator])
        self.assertEqual(match.view_name, 'ns1:ns2:ns3:url_name')
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'arg1': 42, 'arg2': 37})

    def test_from_submatch_ignored_args_inherited_kwargs(self):
        submatch = ResolverMatch(empty_view, (), {'arg1': 42}, 'url_name', decorators=[inner_decorator])
        match = ResolverMatch.from_submatch(submatch, (42, 37), {}, 'app1', 'ns1')
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.url_name, 'url_name')
        self.assertEqual(match.app_name, 'app1')
        self.assertEqual(match.namespace, 'ns1')
        self.assertEqual(match.decorators, [inner_decorator])
        self.assertEqual(match.view_name, 'ns1:url_name')
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'arg1': 42})


@skip("Refactored interals.")
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
        resolver = BaseResolver(constraints=constraints)
        url = '/test/42/'
        request = self.rf.get(url)
        expected = '', (), {'pk': '42'}
        self.assertEqual(resolver.match(url, request), expected)

    def test_no_match(self):
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^test/'),
            RegexPattern(r'^(?P<pk>\d+)/$'),
        ]
        resolver = BaseResolver(constraints=constraints)
        url = '/no/match/'
        request = self.rf.get(url)
        with self.assertRaises(Resolver404):
            resolver.match(url, request)

    def test_empty_constraints_match(self):
        resolver = BaseResolver()
        url = '/test/42/'
        request = self.rf.get(url)
        expected = '/test/42/', (), {}
        self.assertEqual(resolver.match(url, request), expected)

    def test_resolve_to_view(self):
        constraints = [
            RegexPattern(r'^/'),
            RegexPattern(r'^test/$'),
        ]
        resolver = ResolverEndpoint(empty_view, 'empty-view', constraints=constraints)
        url = '/test/'
        request = self.rf.get(url)
        match = resolver.resolve(url, request)
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {})
        self.assertEqual(match.url_name, 'empty-view')

    def test_nested_resolvers(self):
        endpoint = ResolverEndpoint(empty_view, 'empty-view', constraints=[RegexPattern(r'^detail/$')])
        resolver = Resolver([('ns1', endpoint)], 'app1', constraints=[
            RegexPattern(r'^/'),
            RegexPattern(r'^(?P<pk>\d+)/'),
        ])
        url = '/42/detail/'
        request = self.rf.get(url)
        match = resolver.resolve(url, request)
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'pk': '42'})
        self.assertEqual(match.url_name, 'empty-view')
        self.assertEqual(match.app_name, 'app1')
        self.assertEqual(match.namespace, 'ns1')
        self.assertEqual(match.view_name, 'ns1:empty-view')

    def test_decorators(self):
        endpoint = ResolverEndpoint(
            empty_view, 'empty-view', constraints=[RegexPattern(r'^detail/$')],
            decorators=[inner_decorator]
        )
        resolver = Resolver(
            [('ns1', endpoint)], 'app1', constraints=[RegexPattern(r'^/'), RegexPattern(r'^(?P<pk>\d+)/')],
            decorators=[outer_decorator]
        )
        url = '/42/detail/'
        request = self.rf.get(url)
        match = resolver.resolve(url, request)
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'pk': '42'})
        self.assertEqual(match.decorators, [outer_decorator, inner_decorator])

    def test_default_kwargs(self):
        endpoint = ResolverEndpoint(
            empty_view, 'empty-view', constraints=[RegexPattern(r'^detail/$')],
            kwargs={'pk': 'overridden'}
        )
        resolver = Resolver(
            [('ns1', endpoint)], 'app1', constraints=[RegexPattern(r'^/'), RegexPattern(r'^(?P<pk>\d+)/')],
            kwargs={'test2': '37'}
        )
        url = '/42/detail/'
        request = self.rf.get(url)
        match = resolver.resolve(url, request)
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'pk': 'overridden', 'test2': '37'})

    @skip("Removed resolver.search().")
    def test_search_endpoint(self):
        endpoint = ResolverEndpoint(empty_view, 'empty-view', constraints=[RegexPattern(r'^detail/$')])
        count = 0
        for constraints, kwargs in endpoint.search(['empty-view']):
            count += 1
            self.assertEqual(len(constraints), 1)
            self.assertIsInstance(constraints[0], RegexPattern)
            self.assertEqual(constraints[0].regex.pattern, r'^detail/$')
        self.assertEqual(count, 1, "Expected 1 result for endpoint.search(['empty-view']), got %s." % count)
        empty_results = [x for x in endpoint.search(['non-existent'])]
        self.assertEqual(len(empty_results), 0)

    @skip("Removed resolver.search().")
    def test_search_resolver(self):
        endpoint1 = ResolverEndpoint(empty_view, 'empty-view', constraints=[RegexPattern(r'^detail/$')])
        endpoint2 = ResolverEndpoint(empty_view, 'second-view', constraints=[RegexPattern(r'^edit/$')])
        inner_resolver = Resolver(
            [(None, endpoint1), (None, endpoint2)], 'app1', constraints=[RegexPattern(r'^(?P<pk>\d+)/')]
        )
        resolver = Resolver(
            [('ns1', inner_resolver)], constraints=[RegexPattern(r'^/')]
        )
        count = 0
        for constraints, default_kwargs in resolver.search(['ns1', 'empty-view']):
            count += 1
            self.assertEqual(len(constraints), 3)
            self.assertIsInstance(constraints[0], RegexPattern)
            self.assertEqual(constraints[0].regex.pattern, r'^/')
            self.assertIsInstance(constraints[1], RegexPattern)
            self.assertEqual(constraints[1].regex.pattern, r'^(?P<pk>\d+)/')
            self.assertIsInstance(constraints[2], RegexPattern)
            self.assertEqual(constraints[2].regex.pattern, r'^detail/$')
            self.assertEqual(default_kwargs, {})
        self.assertEqual(count, 1)

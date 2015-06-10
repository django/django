from __future__ import unicode_literals

from inspect import getargspec

from django.core.urls import ResolverMatch
from django.test import SimpleTestCase

from .decorators import inner_decorator, outer_decorator
from .views import class_based_view, empty_view


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

    def test_argument_defaults(self):
        match = self.get_resolver_match(url_name=None)
        self.assertEqual(match.url_name, None)
        self.assertEqual(match.namespaces, [])
        self.assertEqual(match.namespace, '')
        self.assertEqual(match.app_names, [])
        self.assertEqual(match.app_name, '')
        self.assertEqual(match.decorators, [])

    def test_function_func_path(self):
        match = self.get_resolver_match()
        self.assertEqual(match._func_path, 'urls.views.empty_view')

    def test_class_func_path(self):
        match = self.get_resolver_match(func=class_based_view)
        self.assertEqual(match._func_path, 'urls.views.ViewClass')

    def test_decorators_reverse_order(self):
        match = self.get_resolver_match(decorators=[outer_decorator, inner_decorator])
        self.assertEqual(match.callback.decorated_by, 'outer')

    def test_decorated_update_wrapper(self):
        match = self.get_resolver_match(decorators=[outer_decorator, inner_decorator])
        self.assertEqual(match.callback.__doc__, empty_view.__doc__)
        self.assertEqual(match.callback.__name__, empty_view.__name__)

    def test_view_name_no_url_name(self):
        match = self.get_resolver_match(url_name=None)
        self.assertEqual(match.view_name, 'urls.views.empty_view')

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

    def test_from_submatch_with_kwargs_no_inherited_args(self):
        submatch = ResolverMatch(
            empty_view, (42, 37), {}, 'url_name', ['app1', 'app2'],
            ['ns1', 'ns2'], [inner_decorator]
        )
        match = ResolverMatch.from_submatch(submatch, (), {'arg1': 42}, decorators=[outer_decorator])
        self.assertEqual(match.__class__, ResolverMatch)
        self.assertEqual(match.url_name, 'url_name')
        self.assertEqual(match.app_name, 'app1:app2')
        self.assertEqual(match.namespace, 'ns1:ns2')
        self.assertEqual(match.decorators, [outer_decorator, inner_decorator])
        self.assertEqual(match.view_name, 'ns1:ns2:url_name')
        self.assertEqual(match.func, empty_view)
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {'arg1': 42})

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
"""
Unit tests for reverse URL lookups.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, resolve, NoReverseMatch,\
                                     Resolver404, ResolverMatch,\
                                     RegexURLResolver, RegexURLPattern
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import redirect
from django.test import TestCase
from django.utils import unittest

import urlconf_outer
import urlconf_inner
import middleware
import views

resolve_test_data = (
    # These entries are in the format: (path, url_name, app_name, namespace, view_func, args, kwargs)
    # Simple case
    ('/normal/42/37/', 'normal-view', None, '', views.empty_view, tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/view_class/42/37/', 'view-class', None, '', views.view_class_instance, tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/included/normal/42/37/', 'inc-normal-view', None, '', views.empty_view, tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/included/view_class/42/37/', 'inc-view-class', None, '', views.view_class_instance, tuple(), {'arg1': '42', 'arg2': '37'}),

    # Unnamed args are dropped if you have *any* kwargs in a pattern
    ('/mixed_args/42/37/', 'mixed-args', None, '', views.empty_view, tuple(), {'arg2': '37'}),
    ('/included/mixed_args/42/37/', 'inc-mixed-args', None, '', views.empty_view, tuple(), {'arg2': '37'}),

    # Unnamed views will be resolved to the function/class name
    ('/unnamed/normal/42/37/', 'regressiontests.urlpatterns_reverse.views.empty_view', None, '', views.empty_view, tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/unnamed/view_class/42/37/', 'regressiontests.urlpatterns_reverse.views.ViewClass', None, '', views.view_class_instance, tuple(), {'arg1': '42', 'arg2': '37'}),

    # If you have no kwargs, you get an args list.
    ('/no_kwargs/42/37/', 'no-kwargs', None, '', views.empty_view, ('42','37'), {}),
    ('/included/no_kwargs/42/37/', 'inc-no-kwargs', None, '', views.empty_view, ('42','37'), {}),

    # Namespaces
    ('/test1/inner/42/37/', 'urlobject-view', 'testapp', 'test-ns1', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/included/test3/inner/42/37/', 'urlobject-view', 'testapp', 'test-ns3', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/ns-included1/normal/42/37/', 'inc-normal-view', None, 'inc-ns1', views.empty_view, tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/included/test3/inner/42/37/', 'urlobject-view', 'testapp', 'test-ns3', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/default/inner/42/37/', 'urlobject-view', 'testapp', 'testapp', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/other2/inner/42/37/', 'urlobject-view', 'nodefault', 'other-ns2', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/other1/inner/42/37/', 'urlobject-view', 'nodefault', 'other-ns1', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),

    # Nested namespaces
    ('/ns-included1/test3/inner/42/37/', 'urlobject-view', 'testapp', 'inc-ns1:test-ns3', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
    ('/ns-included1/ns-included4/ns-included2/test3/inner/42/37/', 'urlobject-view', 'testapp', 'inc-ns1:inc-ns4:inc-ns2:test-ns3', 'empty_view', tuple(), {'arg1': '42', 'arg2': '37'}),
)

test_data = (
    ('places', '/places/3/', [3], {}),
    ('places', '/places/3/', ['3'], {}),
    ('places', NoReverseMatch, ['a'], {}),
    ('places', NoReverseMatch, [], {}),
    ('places?', '/place/', [], {}),
    ('places+', '/places/', [], {}),
    ('places*', '/place/', [], {}),
    ('places2?', '/', [], {}),
    ('places2+', '/places/', [], {}),
    ('places2*', '/', [], {}),
    ('places3', '/places/4/', [4], {}),
    ('places3', '/places/harlem/', ['harlem'], {}),
    ('places3', NoReverseMatch, ['harlem64'], {}),
    ('places4', '/places/3/', [], {'id': 3}),
    ('people', NoReverseMatch, [], {}),
    ('people', '/people/adrian/', ['adrian'], {}),
    ('people', '/people/adrian/', [], {'name': 'adrian'}),
    ('people', NoReverseMatch, ['name with spaces'], {}),
    ('people', NoReverseMatch, [], {'name': 'name with spaces'}),
    ('people2', '/people/name/', [], {}),
    ('people2a', '/people/name/fred/', ['fred'], {}),
    ('optional', '/optional/fred/', [], {'name': 'fred'}),
    ('optional', '/optional/fred/', ['fred'], {}),
    ('hardcoded', '/hardcoded/', [], {}),
    ('hardcoded2', '/hardcoded/doc.pdf', [], {}),
    ('people3', '/people/il/adrian/', [], {'state': 'il', 'name': 'adrian'}),
    ('people3', NoReverseMatch, [], {'state': 'il'}),
    ('people3', NoReverseMatch, [], {'name': 'adrian'}),
    ('people4', NoReverseMatch, [], {'state': 'il', 'name': 'adrian'}),
    ('people6', '/people/il/test/adrian/', ['il/test', 'adrian'], {}),
    ('people6', '/people//adrian/', ['adrian'], {}),
    ('range', '/character_set/a/', [], {}),
    ('range2', '/character_set/x/', [], {}),
    ('price', '/price/$10/', ['10'], {}),
    ('price2', '/price/$10/', ['10'], {}),
    ('price3', '/price/$10/', ['10'], {}),
    ('product', '/product/chocolate+($2.00)/', [], {'price': '2.00', 'product': 'chocolate'}),
    ('headlines', '/headlines/2007.5.21/', [], dict(year=2007, month=5, day=21)),
    ('windows', r'/windows_path/C:%5CDocuments%20and%20Settings%5Cspam/', [], dict(drive_name='C', path=r'Documents and Settings\spam')),
    ('special', r'/special_chars/+%5C$*/', [r'+\$*'], {}),
    ('special', NoReverseMatch, [''], {}),
    ('mixed', '/john/0/', [], {'name': 'john'}),
    ('repeats', '/repeats/a/', [], {}),
    ('repeats2', '/repeats/aa/', [], {}),
    ('repeats3', '/repeats/aa/', [], {}),
    ('insensitive', '/CaseInsensitive/fred', ['fred'], {}),
    ('test', '/test/1', [], {}),
    ('test2', '/test/2', [], {}),
    ('inner-nothing', '/outer/42/', [], {'outer': '42'}),
    ('inner-nothing', '/outer/42/', ['42'], {}),
    ('inner-nothing', NoReverseMatch, ['foo'], {}),
    ('inner-extra', '/outer/42/extra/inner/', [], {'extra': 'inner', 'outer': '42'}),
    ('inner-extra', '/outer/42/extra/inner/', ['42', 'inner'], {}),
    ('inner-extra', NoReverseMatch, ['fred', 'inner'], {}),
    ('disjunction', NoReverseMatch, ['foo'], {}),
    ('inner-disjunction', NoReverseMatch, ['10', '11'], {}),
    ('extra-places', '/e-places/10/', ['10'], {}),
    ('extra-people', '/e-people/fred/', ['fred'], {}),
    ('extra-people', '/e-people/fred/', [], {'name': 'fred'}),
    ('part', '/part/one/', [], {'value': 'one'}),
    ('part', '/prefix/xx/part/one/', [], {'value': 'one', 'prefix': 'xx'}),
    ('part2', '/part2/one/', [], {'value': 'one'}),
    ('part2', '/part2/', [], {}),
    ('part2', '/prefix/xx/part2/one/', [], {'value': 'one', 'prefix': 'xx'}),
    ('part2', '/prefix/xx/part2/', [], {'prefix': 'xx'}),

    # Regression for #9038
    # These views are resolved by method name. Each method is deployed twice -
    # once with an explicit argument, and once using the default value on
    # the method. This is potentially ambiguous, as you have to pick the
    # correct view for the arguments provided.
    ('kwargs_view', '/arg_view/', [], {}),
    ('kwargs_view', '/arg_view/10/', [], {'arg1':10}),
    ('regressiontests.urlpatterns_reverse.views.absolute_kwargs_view', '/absolute_arg_view/', [], {}),
    ('regressiontests.urlpatterns_reverse.views.absolute_kwargs_view', '/absolute_arg_view/10/', [], {'arg1':10}),
    ('non_path_include', '/includes/non_path_include/', [], {})

)

class NoURLPatternsTests(TestCase):
    urls = 'regressiontests.urlpatterns_reverse.no_urls'

    def assertRaisesErrorWithMessage(self, error, message, callable,
        *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))

    def test_no_urls_exception(self):
        """
        RegexURLResolver should raise an exception when no urlpatterns exist.
        """
        resolver = RegexURLResolver(r'^$', self.urls)

        self.assertRaisesErrorWithMessage(ImproperlyConfigured,
            "The included urlconf regressiontests.urlpatterns_reverse.no_urls "\
            "doesn't have any patterns in it", getattr, resolver, 'url_patterns')

class URLPatternReverse(TestCase):
    urls = 'regressiontests.urlpatterns_reverse.urls'

    def test_urlpattern_reverse(self):
        for name, expected, args, kwargs in test_data:
            try:
                got = reverse(name, args=args, kwargs=kwargs)
            except NoReverseMatch, e:
                self.assertEqual(expected, NoReverseMatch)
            else:
                self.assertEquals(got, expected)

    def test_reverse_none(self):
        # Reversing None should raise an error, not return the last un-named view.
        self.assertRaises(NoReverseMatch, reverse, None)

class ResolverTests(unittest.TestCase):
    def test_non_regex(self):
        """
        Verifies that we raise a Resolver404 if what we are resolving doesn't
        meet the basic requirements of a path to match - i.e., at the very
        least, it matches the root pattern '^/'. We must never return None
        from resolve, or we will get a TypeError further down the line.

        Regression for #10834.
        """
        self.assertRaises(Resolver404, resolve, '')
        self.assertRaises(Resolver404, resolve, 'a')
        self.assertRaises(Resolver404, resolve, '\\')
        self.assertRaises(Resolver404, resolve, '.')

    def test_404_tried_urls_have_names(self):
        """
        Verifies that the list of URLs that come back from a Resolver404
        exception contains a list in the right format for printing out in
        the DEBUG 404 page with both the patterns and URL names, if available.
        """
        urls = 'regressiontests.urlpatterns_reverse.named_urls'
        # this list matches the expected URL types and names returned when
        # you try to resolve a non-existent URL in the first level of included
        # URLs in named_urls.py (e.g., '/included/non-existent-url')
        url_types_names = [
            [{'type': RegexURLPattern, 'name': 'named-url1'}],
            [{'type': RegexURLPattern, 'name': 'named-url2'}],
            [{'type': RegexURLPattern, 'name': None}],
            [{'type': RegexURLResolver}, {'type': RegexURLPattern, 'name': 'named-url3'}],
            [{'type': RegexURLResolver}, {'type': RegexURLPattern, 'name': 'named-url4'}],
            [{'type': RegexURLResolver}, {'type': RegexURLPattern, 'name': None}],
            [{'type': RegexURLResolver}, {'type': RegexURLResolver}],
        ]
        try:
            resolve('/included/non-existent-url', urlconf=urls)
            self.fail('resolve did not raise a 404')
        except Resolver404, e:
            # make sure we at least matched the root ('/') url resolver:
            self.assertTrue('tried' in e.args[0])
            tried = e.args[0]['tried']
            self.assertEqual(len(e.args[0]['tried']), len(url_types_names), 'Wrong number of tried URLs returned.  Expected %s, got %s.' % (len(url_types_names), len(e.args[0]['tried'])))
            for tried, expected in zip(e.args[0]['tried'], url_types_names):
                for t, e in zip(tried, expected):
                    self.assertTrue(isinstance(t, e['type']), '%s is not an instance of %s' % (t, e['type']))
                    if 'name' in e:
                        if not e['name']:
                            self.assertTrue(t.name is None, 'Expected no URL name but found %s.' % t.name)
                        else:
                            self.assertEqual(t.name, e['name'], 'Wrong URL name.  Expected "%s", got "%s".' % (e['name'], t.name))

class ReverseShortcutTests(TestCase):
    urls = 'regressiontests.urlpatterns_reverse.urls'

    def test_redirect_to_object(self):
        # We don't really need a model; just something with a get_absolute_url
        class FakeObj(object):
            def get_absolute_url(self):
                return "/hi-there/"

        res = redirect(FakeObj())
        self.assert_(isinstance(res, HttpResponseRedirect))
        self.assertEqual(res['Location'], '/hi-there/')

        res = redirect(FakeObj(), permanent=True)
        self.assert_(isinstance(res, HttpResponsePermanentRedirect))
        self.assertEqual(res['Location'], '/hi-there/')

    def test_redirect_to_view_name(self):
        res = redirect('hardcoded2')
        self.assertEqual(res['Location'], '/hardcoded/doc.pdf')
        res = redirect('places', 1)
        self.assertEqual(res['Location'], '/places/1/')
        res = redirect('headlines', year='2008', month='02', day='17')
        self.assertEqual(res['Location'], '/headlines/2008.02.17/')
        self.assertRaises(NoReverseMatch, redirect, 'not-a-view')

    def test_redirect_to_url(self):
        res = redirect('/foo/')
        self.assertEqual(res['Location'], '/foo/')
        res = redirect('http://example.com/')
        self.assertEqual(res['Location'], 'http://example.com/')

    def test_redirect_view_object(self):
        from views import absolute_kwargs_view
        res = redirect(absolute_kwargs_view)
        self.assertEqual(res['Location'], '/absolute_arg_view/')
        self.assertRaises(NoReverseMatch, redirect, absolute_kwargs_view, wrong_argument=None)


class NamespaceTests(TestCase):
    urls = 'regressiontests.urlpatterns_reverse.namespace_urls'

    def test_ambiguous_object(self):
        "Names deployed via dynamic URL objects that require namespaces can't be resolved"
        self.assertRaises(NoReverseMatch, reverse, 'urlobject-view')
        self.assertRaises(NoReverseMatch, reverse, 'urlobject-view', args=[37,42])
        self.assertRaises(NoReverseMatch, reverse, 'urlobject-view', kwargs={'arg1':42, 'arg2':37})

    def test_ambiguous_urlpattern(self):
        "Names deployed via dynamic URL objects that require namespaces can't be resolved"
        self.assertRaises(NoReverseMatch, reverse, 'inner-nothing')
        self.assertRaises(NoReverseMatch, reverse, 'inner-nothing', args=[37,42])
        self.assertRaises(NoReverseMatch, reverse, 'inner-nothing', kwargs={'arg1':42, 'arg2':37})

    def test_non_existent_namespace(self):
        "Non-existent namespaces raise errors"
        self.assertRaises(NoReverseMatch, reverse, 'blahblah:urlobject-view')
        self.assertRaises(NoReverseMatch, reverse, 'test-ns1:blahblah:urlobject-view')

    def test_normal_name(self):
        "Normal lookups work as expected"
        self.assertEquals('/normal/', reverse('normal-view'))
        self.assertEquals('/normal/37/42/', reverse('normal-view', args=[37,42]))
        self.assertEquals('/normal/42/37/', reverse('normal-view', kwargs={'arg1':42, 'arg2':37}))

    def test_simple_included_name(self):
        "Normal lookups work on names included from other patterns"
        self.assertEquals('/included/normal/', reverse('inc-normal-view'))
        self.assertEquals('/included/normal/37/42/', reverse('inc-normal-view', args=[37,42]))
        self.assertEquals('/included/normal/42/37/', reverse('inc-normal-view', kwargs={'arg1':42, 'arg2':37}))

    def test_namespace_object(self):
        "Dynamic URL objects can be found using a namespace"
        self.assertEquals('/test1/inner/', reverse('test-ns1:urlobject-view'))
        self.assertEquals('/test1/inner/37/42/', reverse('test-ns1:urlobject-view', args=[37,42]))
        self.assertEquals('/test1/inner/42/37/', reverse('test-ns1:urlobject-view', kwargs={'arg1':42, 'arg2':37}))

    def test_embedded_namespace_object(self):
        "Namespaces can be installed anywhere in the URL pattern tree"
        self.assertEquals('/included/test3/inner/', reverse('test-ns3:urlobject-view'))
        self.assertEquals('/included/test3/inner/37/42/', reverse('test-ns3:urlobject-view', args=[37,42]))
        self.assertEquals('/included/test3/inner/42/37/', reverse('test-ns3:urlobject-view', kwargs={'arg1':42, 'arg2':37}))

    def test_namespace_pattern(self):
        "Namespaces can be applied to include()'d urlpatterns"
        self.assertEquals('/ns-included1/normal/', reverse('inc-ns1:inc-normal-view'))
        self.assertEquals('/ns-included1/normal/37/42/', reverse('inc-ns1:inc-normal-view', args=[37,42]))
        self.assertEquals('/ns-included1/normal/42/37/', reverse('inc-ns1:inc-normal-view', kwargs={'arg1':42, 'arg2':37}))

    def test_multiple_namespace_pattern(self):
        "Namespaces can be embedded"
        self.assertEquals('/ns-included1/test3/inner/', reverse('inc-ns1:test-ns3:urlobject-view'))
        self.assertEquals('/ns-included1/test3/inner/37/42/', reverse('inc-ns1:test-ns3:urlobject-view', args=[37,42]))
        self.assertEquals('/ns-included1/test3/inner/42/37/', reverse('inc-ns1:test-ns3:urlobject-view', kwargs={'arg1':42, 'arg2':37}))

    def test_nested_namespace_pattern(self):
        "Namespaces can be nested"
        self.assertEquals('/ns-included1/ns-included4/ns-included1/test3/inner/', reverse('inc-ns1:inc-ns4:inc-ns1:test-ns3:urlobject-view'))
        self.assertEquals('/ns-included1/ns-included4/ns-included1/test3/inner/37/42/', reverse('inc-ns1:inc-ns4:inc-ns1:test-ns3:urlobject-view', args=[37,42]))
        self.assertEquals('/ns-included1/ns-included4/ns-included1/test3/inner/42/37/', reverse('inc-ns1:inc-ns4:inc-ns1:test-ns3:urlobject-view', kwargs={'arg1':42, 'arg2':37}))

    def test_app_lookup_object(self):
        "A default application namespace can be used for lookup"
        self.assertEquals('/default/inner/', reverse('testapp:urlobject-view'))
        self.assertEquals('/default/inner/37/42/', reverse('testapp:urlobject-view', args=[37,42]))
        self.assertEquals('/default/inner/42/37/', reverse('testapp:urlobject-view', kwargs={'arg1':42, 'arg2':37}))

    def test_app_lookup_object_with_default(self):
        "A default application namespace is sensitive to the 'current' app can be used for lookup"
        self.assertEquals('/included/test3/inner/', reverse('testapp:urlobject-view', current_app='test-ns3'))
        self.assertEquals('/included/test3/inner/37/42/', reverse('testapp:urlobject-view', args=[37,42], current_app='test-ns3'))
        self.assertEquals('/included/test3/inner/42/37/', reverse('testapp:urlobject-view', kwargs={'arg1':42, 'arg2':37}, current_app='test-ns3'))

    def test_app_lookup_object_without_default(self):
        "An application namespace without a default is sensitive to the 'current' app can be used for lookup"
        self.assertEquals('/other2/inner/', reverse('nodefault:urlobject-view'))
        self.assertEquals('/other2/inner/37/42/', reverse('nodefault:urlobject-view', args=[37,42]))
        self.assertEquals('/other2/inner/42/37/', reverse('nodefault:urlobject-view', kwargs={'arg1':42, 'arg2':37}))

        self.assertEquals('/other1/inner/', reverse('nodefault:urlobject-view', current_app='other-ns1'))
        self.assertEquals('/other1/inner/37/42/', reverse('nodefault:urlobject-view', args=[37,42], current_app='other-ns1'))
        self.assertEquals('/other1/inner/42/37/', reverse('nodefault:urlobject-view', kwargs={'arg1':42, 'arg2':37}, current_app='other-ns1'))

class RequestURLconfTests(TestCase):
    def setUp(self):
        self.root_urlconf = settings.ROOT_URLCONF
        self.middleware_classes = settings.MIDDLEWARE_CLASSES
        settings.ROOT_URLCONF = urlconf_outer.__name__

    def tearDown(self):
        settings.ROOT_URLCONF = self.root_urlconf
        settings.MIDDLEWARE_CLASSES = self.middleware_classes

    def test_urlconf(self):
        response = self.client.get('/test/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'outer:/test/me/,'
                                           'inner:/inner_urlconf/second_test/')
        response = self.client.get('/inner_urlconf/second_test/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/second_test/')
        self.assertEqual(response.status_code, 404)

    def test_urlconf_overridden(self):
        settings.MIDDLEWARE_CLASSES += (
            '%s.ChangeURLconfMiddleware' % middleware.__name__,
        )
        response = self.client.get('/test/me/')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/inner_urlconf/second_test/')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/second_test/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'outer:,inner:/second_test/')

    def test_urlconf_overridden_with_null(self):
        settings.MIDDLEWARE_CLASSES += (
            '%s.NullChangeURLconfMiddleware' % middleware.__name__,
        )
        self.assertRaises(ImproperlyConfigured, self.client.get, '/test/me/')

class ErrorHandlerResolutionTests(TestCase):
    """Tests for handler404 and handler500"""

    def setUp(self):
        from django.core.urlresolvers import RegexURLResolver
        urlconf = 'regressiontests.urlpatterns_reverse.urls_error_handlers'
        urlconf_callables = 'regressiontests.urlpatterns_reverse.urls_error_handlers_callables'
        self.resolver = RegexURLResolver(r'^$', urlconf)
        self.callable_resolver = RegexURLResolver(r'^$', urlconf_callables)

    def test_named_handlers(self):
        from views import empty_view
        handler = (empty_view, {})
        self.assertEqual(self.resolver.resolve404(), handler)
        self.assertEqual(self.resolver.resolve500(), handler)

    def test_callable_handers(self):
        from views import empty_view
        handler = (empty_view, {})
        self.assertEqual(self.callable_resolver.resolve404(), handler)
        self.assertEqual(self.callable_resolver.resolve500(), handler)

class DefaultErrorHandlerTests(TestCase):
    urls = 'regressiontests.urlpatterns_reverse.urls_without_full_import'

    def test_default_handler(self):
        "If the urls.py doesn't specify handlers, the defaults are used"
        try:
            response = self.client.get('/test/')
            self.assertEquals(response.status_code, 404)
        except AttributeError:
            self.fail("Shouldn't get an AttributeError due to undefined 404 handler")

        try:
            self.assertRaises(ValueError, self.client.get, '/bad_view/')
        except AttributeError:
            self.fail("Shouldn't get an AttributeError due to undefined 500 handler")

class NoRootUrlConfTests(TestCase):
    """Tests for handler404 and handler500 if urlconf is None"""
    urls = None

    def test_no_handler_exception(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/test/me/')

class ResolverMatchTests(TestCase):
    urls = 'regressiontests.urlpatterns_reverse.namespace_urls'

    def test_urlpattern_resolve(self):
        for path, name, app_name, namespace, func, args, kwargs in resolve_test_data:
            # Test legacy support for extracting "function, args, kwargs"
            match_func, match_args, match_kwargs = resolve(path)
            self.assertEqual(match_func, func)
            self.assertEqual(match_args, args)
            self.assertEqual(match_kwargs, kwargs)

            # Test ResolverMatch capabilities.
            match = resolve(path)
            self.assertEqual(match.__class__, ResolverMatch)
            self.assertEqual(match.url_name, name)
            self.assertEqual(match.args, args)
            self.assertEqual(match.kwargs, kwargs)
            self.assertEqual(match.app_name, app_name)
            self.assertEqual(match.namespace, namespace)
            self.assertEqual(match.func, func)

            # ... and for legacy purposes:
            self.assertEquals(match[0], func)
            self.assertEquals(match[1], args)
            self.assertEquals(match[2], kwargs)

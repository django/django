"""
Unit tests for reverse URL lookups.
"""
__test__ = {'API_TESTS': """

RegexURLResolver should raise an exception when no urlpatterns exist.

>>> from django.core.urlresolvers import RegexURLResolver
>>> no_urls = 'regressiontests.urlpatterns_reverse.no_urls'
>>> resolver = RegexURLResolver(r'^$', no_urls)
>>> resolver.url_patterns
Traceback (most recent call last):
...
ImproperlyConfigured: The included urlconf regressiontests.urlpatterns_reverse.no_urls doesn't have any patterns in it
"""}

import unittest

from django.core.urlresolvers import reverse, resolve, NoReverseMatch, Resolver404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import redirect
from django.test import TestCase

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
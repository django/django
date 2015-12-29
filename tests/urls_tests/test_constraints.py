# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.test import SimpleTestCase
from django.urls import URL, NoReverseMatch, RegexPattern, Resolver404

regex_match_data = (
    # format: (regex, url, new_url, captured_args, captured_kwargs)
    (r'^$', '', ('', (), {})),
    (r'^$', '/', Resolver404),
    (r'^', '/', ('/', (), {})),
    (r'^test/$', 'test/', ('', (), {})),
    (r'^(?P<pk>\d+)/$', '15/', ('', (), {'pk': '15'})),
    (r'^(\d+)/$', '42/', ('', ('42',), {})),
    # Don't mix named and unnamed groups
    (r'^([\w-]+)/(?P<pk>\d+)/$', 'test/37/', ('', (), {'pk': '37'})),

    (r'^(?P<pk>\d+)/', '21/test/', ('test/', (), {'pk': '21'})),
    (r'test/', 'some/prefix/test/trailing/', ('trailing/', (), {})),

    # unicode characters
    (r'^I ♥ Django/$', 'I ♥ Django/', ('', (), {})),
)


regex_construct_data = (
    # format: (regex, args, kwargs, expected)
    (r'^$', (), {}, ('', (), {})),
    (r'^test/$', (), {}, ('test/', (), {})),
    (r'test/', (), {}, ('test/', (), {})),
    (r'^(\d+)/$', ('42',), {}, ('42/', (), {})),
    (r'^(?P<pk>\d+)/$', (), {'pk': '42'}, ('42/', (), {})),
    (r'^(\d+)/$', (), {}, NoReverseMatch),
    (r'^(?P<pk>\d+)/$', (), {}, NoReverseMatch),
    # Can't use kwargs to reconstruct unnamed groups
    (r'^(\d+)/$', (), {'pk': '42'}, NoReverseMatch),
    # But can use args to reconstruct named groups
    (r'^(?P<pk>\d+)/$', ('42',), {}, ('42/', (), {})),

    (r'^(\d+)/', ('42', '37'), {}, ('42/', ('37',), {})),
    (r'^(?P<pk>\d+)/', (), {'pk': '42', 'slug': 'test'}, ('42/', (), {'slug': 'test'})),
)


class ConstraintTestCase(SimpleTestCase):
    def assertMatchEqual(self, constraint, url, request, expected):
        try:
            got = constraint.match(url, request)
        except Resolver404:
            self.assertEqual(expected, Resolver404)
        else:
            self.assertEqual(got, expected)


class RegexPatternTests(ConstraintTestCase):
    def test_regex_pattern(self):
        pattern = RegexPattern(r'^test/$')
        self.assertEqual(pattern.regex.pattern, r'^test/$')
        self.assertEqual(pattern.normalized_patterns, [('test/', [])])
        self.assertIsInstance(pattern.regex, re._pattern_type)

    def test_describe(self):
        pattern = RegexPattern(r'^test/$')
        self.assertEqual(pattern.describe(URL()).describe(), r'^test/$')
        other_pattern = RegexPattern(r'test/$')
        self.assertEqual(other_pattern.describe(URL()).describe(), r'test/$')

    def test_regex_match(self):
        for regex, url, expected in regex_match_data:
            pattern = RegexPattern(regex)
            self.assertMatchEqual(pattern, url, None, expected)

    def test_regex_construct(self):
        for regex, args, kwargs, expected in regex_construct_data:
            pattern = RegexPattern(regex)
            url = URL()
            try:
                url, args, kwargs = pattern.construct(url, *args, **kwargs)
            except NoReverseMatch:
                self.assertEqual(expected, NoReverseMatch)
            else:
                self.assertEqual((url.path, args, kwargs), expected)

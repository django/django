# coding: utf-8
from __future__ import unicode_literals

from django.test import TestCase
from django.utils.encoding import iri_to_uri, force_text
from django.utils.functional import lazy
from django.utils.http import (cookie_date, http_date,
    urlquote, urlquote_plus, urlunquote, urlunquote_plus)
from django.utils import six
from django.utils.text import get_text_list, smart_split
from django.utils.translation import override

lazystr = lazy(force_text, six.text_type)


class TextTests(TestCase):
    """
    Tests for stuff in django.utils.text and other text munging util functions.
    """

    def test_get_text_list(self):
        self.assertEqual(get_text_list(['a', 'b', 'c', 'd']), 'a, b, c or d')
        self.assertEqual(get_text_list(['a', 'b', 'c'], 'and'), 'a, b and c')
        self.assertEqual(get_text_list(['a', 'b'], 'and'), 'a and b')
        self.assertEqual(get_text_list(['a']), 'a')
        self.assertEqual(get_text_list([]), '')
        with override('ar'):
            self.assertEqual(get_text_list(['a', 'b', 'c']), "a، b أو c")

    def test_smart_split(self):

        testdata = [
            ('This is "a person" test.',
                ['This', 'is', '"a person"', 'test.']),
            ('This is "a person\'s" test.',
                ['This', 'is', '"a person\'s"', 'test.']),
            ('This is "a person\\"s" test.',
                ['This', 'is', '"a person\\"s"', 'test.']),
            ('"a \'one',
                ['"a', "'one"]),
            ('all friends\' tests',
                ['all', 'friends\'', 'tests']),
            ('url search_page words="something else"',
                ['url', 'search_page', 'words="something else"']),
            ("url search_page words='something else'",
                ['url', 'search_page', "words='something else'"]),
            ('url search_page words "something else"',
                ['url', 'search_page', 'words', '"something else"']),
            ('url search_page words-"something else"',
                ['url', 'search_page', 'words-"something else"']),
            ('url search_page words=hello',
                ['url', 'search_page', 'words=hello']),
            ('url search_page words="something else',
                ['url', 'search_page', 'words="something', 'else']),
            ("cut:','|cut:' '",
                ["cut:','|cut:' '"]),
            (lazystr("a b c d"),  # Test for #20231
                ['a', 'b', 'c', 'd']),
        ]
        for test, expected in testdata:
            self.assertEqual(list(smart_split(test)), expected)

    def test_urlquote(self):
        self.assertEqual(urlquote('Paris & Orl\xe9ans'),
            'Paris%20%26%20Orl%C3%A9ans')
        self.assertEqual(urlquote('Paris & Orl\xe9ans', safe="&"),
            'Paris%20&%20Orl%C3%A9ans')
        self.assertEqual(
            urlunquote('Paris%20%26%20Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')
        self.assertEqual(
            urlunquote('Paris%20&%20Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')
        self.assertEqual(urlquote_plus('Paris & Orl\xe9ans'),
            'Paris+%26+Orl%C3%A9ans')
        self.assertEqual(urlquote_plus('Paris & Orl\xe9ans', safe="&"),
            'Paris+&+Orl%C3%A9ans')
        self.assertEqual(
            urlunquote_plus('Paris+%26+Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')
        self.assertEqual(
            urlunquote_plus('Paris+&+Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')

    def test_cookie_date(self):
        t = 1167616461.0
        self.assertEqual(cookie_date(t), 'Mon, 01-Jan-2007 01:54:21 GMT')

    def test_http_date(self):
        t = 1167616461.0
        self.assertEqual(http_date(t), 'Mon, 01 Jan 2007 01:54:21 GMT')

    def test_iri_to_uri(self):
        self.assertEqual(iri_to_uri('red%09ros\xe9#red'),
            'red%09ros%C3%A9#red')

        self.assertEqual(iri_to_uri('/blog/for/J\xfcrgen M\xfcnster/'),
            '/blog/for/J%C3%BCrgen%20M%C3%BCnster/')

        self.assertEqual(iri_to_uri('locations/%s' % urlquote_plus('Paris & Orl\xe9ans')),
            'locations/Paris+%26+Orl%C3%A9ans')

    def test_iri_to_uri_idempotent(self):
        self.assertEqual(iri_to_uri(iri_to_uri('red%09ros\xe9#red')),
            'red%09ros%C3%A9#red')

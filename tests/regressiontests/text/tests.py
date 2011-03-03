# coding: utf-8
from django.test import TestCase

from django.utils.text import *
from django.utils.http import urlquote, urlquote_plus, cookie_date, http_date
from django.utils.encoding import iri_to_uri
from django.utils.translation import activate, deactivate

class TextTests(TestCase):
    """
    Tests for stuff in django.utils.text and other text munging util functions.
    """

    def test_get_text_list(self):
        self.assertEqual(get_text_list(['a', 'b', 'c', 'd']), u'a, b, c or d')
        self.assertEqual(get_text_list(['a', 'b', 'c'], 'and'), u'a, b and c')
        self.assertEqual(get_text_list(['a', 'b'], 'and'), u'a and b')
        self.assertEqual(get_text_list(['a']), u'a')
        self.assertEqual(get_text_list([]), u'')
        activate('ar')
        self.assertEqual(get_text_list(['a', 'b', 'c']), u"a، b أو c")
        deactivate()

    def test_smart_split(self):

        self.assertEqual(list(smart_split(r'''This is "a person" test.''')),
            [u'This', u'is', u'"a person"', u'test.'])

        self.assertEqual(list(smart_split(r'''This is "a person's" test.'''))[2],
            u'"a person\'s"')

        self.assertEqual(list(smart_split(r'''This is "a person\"s" test.'''))[2],
            u'"a person\\"s"')

        self.assertEqual(list(smart_split('''"a 'one''')), [u'"a', u"'one"])

        self.assertEqual(list(smart_split(r'''all friends' tests'''))[1],
            "friends'")

        self.assertEqual(list(smart_split(u'url search_page words="something else"')),
            [u'url', u'search_page', u'words="something else"'])

        self.assertEqual(list(smart_split(u"url search_page words='something else'")),
            [u'url', u'search_page', u"words='something else'"])

        self.assertEqual(list(smart_split(u'url search_page words "something else"')),
            [u'url', u'search_page', u'words', u'"something else"'])

        self.assertEqual(list(smart_split(u'url search_page words-"something else"')),
            [u'url', u'search_page', u'words-"something else"'])

        self.assertEqual(list(smart_split(u'url search_page words=hello')),
            [u'url', u'search_page', u'words=hello'])

        self.assertEqual(list(smart_split(u'url search_page words="something else')),
            [u'url', u'search_page', u'words="something', u'else'])

        self.assertEqual(list(smart_split("cut:','|cut:' '")),
            [u"cut:','|cut:' '"])

    def test_urlquote(self):

        self.assertEqual(urlquote(u'Paris & Orl\xe9ans'),
            u'Paris%20%26%20Orl%C3%A9ans')
        self.assertEqual(urlquote(u'Paris & Orl\xe9ans', safe="&"),
            u'Paris%20&%20Orl%C3%A9ans')
        self.assertEqual(urlquote_plus(u'Paris & Orl\xe9ans'),
            u'Paris+%26+Orl%C3%A9ans')
        self.assertEqual(urlquote_plus(u'Paris & Orl\xe9ans', safe="&"),
            u'Paris+&+Orl%C3%A9ans')

    def test_cookie_date(self):
        t = 1167616461.0
        self.assertEqual(cookie_date(t), 'Mon, 01-Jan-2007 01:54:21 GMT')

    def test_http_date(self):
        t = 1167616461.0
        self.assertEqual(http_date(t), 'Mon, 01 Jan 2007 01:54:21 GMT')

    def test_iri_to_uri(self):
        self.assertEqual(iri_to_uri(u'red%09ros\xe9#red'),
            'red%09ros%C3%A9#red')

        self.assertEqual(iri_to_uri(u'/blog/for/J\xfcrgen M\xfcnster/'),
            '/blog/for/J%C3%BCrgen%20M%C3%BCnster/')

        self.assertEqual(iri_to_uri(u'locations/%s' % urlquote_plus(u'Paris & Orl\xe9ans')),
            'locations/Paris+%26+Orl%C3%A9ans')

    def test_iri_to_uri_idempotent(self):
        self.assertEqual(iri_to_uri(iri_to_uri(u'red%09ros\xe9#red')),
            'red%09ros%C3%A9#red')

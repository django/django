# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urls import URL
from django.test import SimpleTestCase

full_path_data = (
    # format: (path, query_string, fragment, expected)
    ('/test/', 'query=true', 'fragment', '/test/?query=true#fragment'),
    # and empty path still returns a slash
    ('', '', '', '/'),
    # ?, = and ; in the path must be encoded
    ('/test/?=;', '', '', '/test/%3F%3D%3B'),
    # other "reserved" characters don't have to be encoded
    ('/test/@&$', '', '', '/test/@&$'),
    # # in query string must be encoded
    ('/test/', 'query=#hashtag', 'fragment', '/test/?query=%23hashtag#fragment'),
    # / and ? in query string are allowed
    ('/test/', 'query/string=what?', '', '/test/?query/string=what?'),
    # # in fragment is allowed
    ('/test/', '', '#fragment#', '/test/##fragment#'),
    # characters outside ASCII range are encoded in the path
    ('/I ♥ Django/', '', '', '/I%20%E2%99%A5%20Django/'),
    # and in the query string
    ('/test/', 'django=♥', '', '/test/?django=%E2%99%A5'),
    # and in the fragment
    ('/test/', '', '♥', '/test/#%E2%99%A5'),
)


class URLTests(SimpleTestCase):
    def test_url_path(self):
        for path, query, fragment, expected in full_path_data:
            url = URL(path=path, query_string=query, fragment=fragment)
            self.assertEqual(
                str(url), expected,
                "URL(path=%s, query_string=%s, fragment=%s) does not match %s" %
                (path, query, fragment, expected),
            )
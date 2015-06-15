# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urls import URL
from django.test import SimpleTestCase

get_full_path_data = (
    # format: (path, query_string, fragment, force_append_slash, expected)
    ('/test/', 'query=true', 'fragment', False, '/test/?query=true#fragment'),
    # and empty path still returns a slash
    ('', '', '', False, '/'),
    # ?, = and ; in the path must be encoded
    ('/test/?=;', '', '', False, '/test/%3F%3D%3B'),
    # other "reserved" characters don't have to be encoded
    ('/test/@&$', '', '', False, '/test/@&$'),
    # # in query string must be encoded
    ('/test/', 'query=#hashtag', 'fragment', False, '/test/?query=%23hashtag#fragment'),
    # / and ? in query string are allowed
    ('/test/', 'query/string=what?', '', False, '/test/?query/string=what?'),
    # # in fragment is allowed
    ('/test/', '', '#fragment#', False, '/test/##fragment#'),
    # force_append_slash adds a slash if path doesn't end with one
    ('/test', '', '', True, '/test/'),
    # even with a query string and/or fragment
    ('/test', 'query=true', 'fragment', True, '/test/?query=true#fragment'),
    # but not if it already ends with a slash
    ('/test/', '', '', True, '/test/'),
    # characters outside ASCII range are encoded in the path
    ('/I ♥ Django/', '', '', False, '/I%20%E2%99%A5%20Django/'),
    # and in the query string
    ('/test/', 'django=♥', '', False, '/test/?django=%E2%99%A5'),
    # and in the fragment
    ('/test/', '', '♥', False, '/test/#%E2%99%A5'),
)

build_absolute_path_data = (
    # format: (current_path, location, expected)
    ('', '', '/'),
    ('/', '/test/', '/test/'),
    ('/', 'test/', '/test/'),
    ('/test/', '', '/test/'),
    ('/test/', '.', '/test/'),
    ('/test/', '../', '/'),
    ('/test/', 'relative', '/test/relative'),
    ('/test/', 'relative/', '/test/relative/'),
    ('/test', 'relative', '/relative'),
    ('/test', 'relative/', '/relative/'),
    ('/test', '.', '/'),
    ('/test', '..', '/'),
    # Examples from RFC3986 section 5.4
    ('/b/c/d', 'g', '/b/c/g'),
    ('/b/c/d', './g', '/b/c/g'),
    ('/b/c/d', 'g/', '/b/c/g/'),
    ('/b/c/d', 'g', '/b/c/g'),
    ('/b/c/d', '', '/b/c/d'),
    ('/b/c/d', '.', '/b/c/'),
    ('/b/c/d', './', '/b/c/'),
    ('/b/c/d', '..', '/b/'),
    ('/b/c/d', '../', '/b/'),
    ('/b/c/d', '../g', '/b/g'),
    ('/b/c/d', '../..', '/'),
    ('/b/c/d', '../../', '/'),
    ('/b/c/d', '../../g', '/g'),

    ('/b/c/d', '../../../g', '/g'),
    ('/b/c/d', '../../../../g', '/g'),
    ('/b/c/d', '/./g', '/g'),
    ('/b/c/d', '/../g', '/g'),
    ('/b/c/d', 'g.', '/b/c/g.'),
    ('/b/c/d', '.g', '/b/c/.g'),
    ('/b/c/d', 'g..', '/b/c/g..'),
    ('/b/c/d', '..g', '/b/c/..g'),

    ('/b/c/d', './../g', '/b/g'),
    ('/b/c/d', './g/.', '/b/c/g/'),
    ('/b/c/d', 'g/./h', '/b/c/g/h'),
    ('/b/c/d', 'g/../h', '/b/c/h'),
    ('/b/c/d', 'g', '/b/c/g'),
)


class URLTests(SimpleTestCase):
    def test_url_get_full_path(self):
        self.assertTrue(get_full_path_data, "get_full_path_data is empty.")
        for path, query_string, fragment, force_append_slash, expected in get_full_path_data:
            url = URL(path=path, query_string=query_string, fragment=fragment)
            self.assertEqual(url.get_full_path(force_append_slash), expected)

    def test_url_build_absolute_path(self):
        self.assertTrue(build_absolute_path_data, "build_absolute_path_data is empty.")
        for current_path, location, expected in build_absolute_path_data:
            url = URL(path=current_path)
            self.assertEqual(
                url.build_absolute_path(location), expected,
                'URL(path=%r).build_absolute_path(%r) did not resolve to %r' %
                (current_path, location, expected)
            )
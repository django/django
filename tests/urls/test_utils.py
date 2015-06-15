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


build_absolute_uri_data = (
    ('http://example.org/current/path/', '/test/', 'http://example.org/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path', 'test/', 'http://example.org/current/test/'),
    ('http://example.org:8000/current/path/', '/test/', 'http://example.org:8000/test/'),
    ('http://example.org:8000/current/path/', 'test/', 'http://example.org:8000/current/path/test/'),
    ('http://example.org:8000/current/path', 'test/', 'http://example.org:8000/current/test/'),

    ('http://example.org/current/path/', '//test.com/test/', 'http://test.com/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('http://example.org/current/path/', 'test/', 'http://example.org/current/path/test/'),
    ('/test/', '/', '/'),
    ('//example.org/', '/test/', '//example.org/test/'),
    # Examples from RFC 3986 section 5.4
    ("http://a/b/c/d;p?q", "g:h", "g:h"),
    ("http://a/b/c/d;p?q", "g", "http://a/b/c/g"),
    ("http://a/b/c/d;p?q", "./g", "http://a/b/c/g"),
    ("http://a/b/c/d;p?q", "g/", "http://a/b/c/g/"),
    ("http://a/b/c/d;p?q", "/g", "http://a/g"),
    ("http://a/b/c/d;p?q", "//g", "http://g"),
    ("http://a/b/c/d;p?q", "?y", "http://a/b/c/d;p?y"),
    ("http://a/b/c/d;p?q", "g?y", "http://a/b/c/g?y"),
    ("http://a/b/c/d;p?q", "#s", "http://a/b/c/d;p?q#s"),
    ("http://a/b/c/d;p?q", "g#s", "http://a/b/c/g#s"),
    ("http://a/b/c/d;p?q", "g?y#s", "http://a/b/c/g?y#s"),
    ("http://a/b/c/d;p?q", ";x", "http://a/b/c/;x"),
    ("http://a/b/c/d;p?q", "g;x",  "http://a/b/c/g;x"),
    ("http://a/b/c/d;p?q", "g;x?y#s", "http://a/b/c/g;x?y#s"),
    ("http://a/b/c/d;p?q", "", "http://a/b/c/d;p?q"),
    ("http://a/b/c/d;p?q", ".", "http://a/b/c/"),
    ("http://a/b/c/d;p?q", "./", "http://a/b/c/"),
    ("http://a/b/c/d;p?q", "..", "http://a/b/"),
    ("http://a/b/c/d;p?q", "../", "http://a/b/"),
    ("http://a/b/c/d;p?q", "../g", "http://a/b/g"),
    ("http://a/b/c/d;p?q", "../..", "http://a/"),
    ("http://a/b/c/d;p?q", "../../", "http://a/"),
    ("http://a/b/c/d;p?q", "../../g", "http://a/g"),
    ("http://a/b/c/d;p?q", "../../../g", "http://a/g"),
    ("http://a/b/c/d;p?q", "../../../../g", "http://a/g"),
    ("http://a/b/c/d;p?q", "/./g", "http://a/g"),
    ("http://a/b/c/d;p?q", "/../g", "http://a/g"),
    ("http://a/b/c/d;p?q", "g.", "http://a/b/c/g."),
    ("http://a/b/c/d;p?q", ".g", "http://a/b/c/.g"),
    ("http://a/b/c/d;p?q", "g..", "http://a/b/c/g.."),
    ("http://a/b/c/d;p?q", "..g", "http://a/b/c/..g"),
    ("http://a/b/c/d;p?q", "./../g", "http://a/b/g"),
    ("http://a/b/c/d;p?q", "./g/.", "http://a/b/c/g/"),
    ("http://a/b/c/d;p?q", "g/./h", "http://a/b/c/g/h"),
    ("http://a/b/c/d;p?q", "g/../h", "http://a/b/c/h"),
    ("http://a/b/c/d;p?q", "g;x=1/./y", "http://a/b/c/g;x=1/y"),
    ("http://a/b/c/d;p?q", "g;x=1/../y", "http://a/b/c/y"),
    ("http://a/b/c/d;p?q", "g?y/./x", "http://a/b/c/g?y/./x"),
    ("http://a/b/c/d;p?q", "g?y/../x", "http://a/b/c/g?y/../x"),
    ("http://a/b/c/d;p?q", "g#s/./x", "http://a/b/c/g#s/./x"),
    ("http://a/b/c/d;p?q", "g#s/../x", "http://a/b/c/g#s/../x"),
)


build_relative_uri_data = (

    # Examples from RFC 3986 section 5.4
    ("http://a/b/c/d;p?q", "g:h", "g:h"),
    ("http://a/b/c/d;p?q", "g", "/b/c/g"),
    ("http://a/b/c/d;p?q", "./g", "/b/c/g"),
    ("http://a/b/c/d;p?q", "g/", "/b/c/g/"),
    ("http://a/b/c/d;p?q", "/g", "/g"),
    ("http://a/b/c/d;p?q", "//g", "//g"),
    ("http://a/b/c/d;p?q", "?y", "/b/c/d;p?y"),
    ("http://a/b/c/d;p?q", "g?y", "/b/c/g?y"),
    ("http://a/b/c/d;p?q", "#s", "/b/c/d;p?q#s"),
    ("http://a/b/c/d;p?q", "g#s", "/b/c/g#s"),
    ("http://a/b/c/d;p?q", "g?y#s", "/b/c/g?y#s"),
    ("http://a/b/c/d;p?q", ";x", "/b/c/;x"),
    ("http://a/b/c/d;p?q", "g;x",  "/b/c/g;x"),
    ("http://a/b/c/d;p?q", "g;x?y#s", "/b/c/g;x?y#s"),
    ("http://a/b/c/d;p?q", "", "/b/c/d;p?q"),
    ("http://a/b/c/d;p?q", ".", "/b/c/"),
    ("http://a/b/c/d;p?q", "./", "/b/c/"),
    ("http://a/b/c/d;p?q", "..", "/b/"),
    ("http://a/b/c/d;p?q", "../", "/b/"),
    ("http://a/b/c/d;p?q", "../g", "/b/g"),
    ("http://a/b/c/d;p?q", "../..", "/"),
    ("http://a/b/c/d;p?q", "../../", "/"),
    ("http://a/b/c/d;p?q", "../../g", "/g"),
    ("http://a/b/c/d;p?q", "../../../g", "/g"),
    ("http://a/b/c/d;p?q", "../../../../g", "/g"),
    ("http://a/b/c/d;p?q", "/./g", "/g"),
    ("http://a/b/c/d;p?q", "/../g", "/g"),
    ("http://a/b/c/d;p?q", "g.", "/b/c/g."),
    ("http://a/b/c/d;p?q", ".g", "/b/c/.g"),
    ("http://a/b/c/d;p?q", "g..", "/b/c/g.."),
    ("http://a/b/c/d;p?q", "..g", "/b/c/..g"),
    ("http://a/b/c/d;p?q", "./../g", "/b/g"),
    ("http://a/b/c/d;p?q", "./g/.", "/b/c/g/"),
    ("http://a/b/c/d;p?q", "g/./h", "/b/c/g/h"),
    ("http://a/b/c/d;p?q", "g/../h", "/b/c/h"),
    ("http://a/b/c/d;p?q", "g;x=1/./y", "/b/c/g;x=1/y"),
    ("http://a/b/c/d;p?q", "g;x=1/../y", "/b/c/y"),
    ("http://a/b/c/d;p?q", "g?y/./x", "/b/c/g?y/./x"),
    ("http://a/b/c/d;p?q", "g?y/../x", "/b/c/g?y/../x"),
    ("http://a/b/c/d;p?q", "g#s/./x", "/b/c/g#s/./x"),
    ("http://a/b/c/d;p?q", "g#s/../x", "/b/c/g#s/../x"),
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

    def test_url_build_absolute_uri(self):
        self.assertTrue(build_absolute_uri_data, "build_absolute_uri_data is empty.")
        for current_uri, location, expected in build_absolute_uri_data:
            url = URL.from_location(current_uri)
            self.assertEqual(
                url.build_absolute_url(location), expected,
                "URL.from_location(%r).build_absolute_url(%r) did not resolve to %r" %
                (current_uri, location, expected)
            )

    def test_url_build_relative_uri(self):
        self.assertTrue(build_relative_uri_data, "build_relative_uri_data is empty.")
        for current_uri, location, expected in build_relative_uri_data:
            url = URL.from_location(current_uri)
            self.assertEqual(
                url.build_relative_url(location), expected,
                "URL.from_location(%r).build_relative_url(%r) did not resolve to %r" %
                (current_uri, location, expected)
            )
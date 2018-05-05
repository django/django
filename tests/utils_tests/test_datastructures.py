"""
Tests for stuff in django.utils.datastructures.
"""

import copy

from django.test import SimpleTestCase
from django.utils.datastructures import (
    DictWrapper, ImmutableList, MultiValueDict, MultiValueDictKeyError,
    OrderedSet, ImmutableCaseInsensitiveDict, EnvironHeaders
)


class OrderedSetTests(SimpleTestCase):

    def test_bool(self):
        # Refs #23664
        s = OrderedSet()
        self.assertFalse(s)
        s.add(1)
        self.assertTrue(s)

    def test_len(self):
        s = OrderedSet()
        self.assertEqual(len(s), 0)
        s.add(1)
        s.add(2)
        s.add(2)
        self.assertEqual(len(s), 2)


class MultiValueDictTests(SimpleTestCase):

    def test_multivaluedict(self):
        d = MultiValueDict({'name': ['Adrian', 'Simon'],
                            'position': ['Developer']})

        self.assertEqual(d['name'], 'Simon')
        self.assertEqual(d.get('name'), 'Simon')
        self.assertEqual(d.getlist('name'), ['Adrian', 'Simon'])
        self.assertEqual(
            sorted(d.items()),
            [('name', 'Simon'), ('position', 'Developer')]
        )

        self.assertEqual(
            sorted(d.lists()),
            [('name', ['Adrian', 'Simon']), ('position', ['Developer'])]
        )

        with self.assertRaises(MultiValueDictKeyError) as cm:
            d.__getitem__('lastname')
        self.assertEqual(str(cm.exception), "'lastname'")

        self.assertIsNone(d.get('lastname'))
        self.assertEqual(d.get('lastname', 'nonexistent'), 'nonexistent')
        self.assertEqual(d.getlist('lastname'), [])
        self.assertEqual(d.getlist('doesnotexist', ['Adrian', 'Simon']),
                         ['Adrian', 'Simon'])

        d.setlist('lastname', ['Holovaty', 'Willison'])
        self.assertEqual(d.getlist('lastname'), ['Holovaty', 'Willison'])
        self.assertEqual(sorted(d.values()), ['Developer', 'Simon', 'Willison'])

    def test_appendlist(self):
        d = MultiValueDict()
        d.appendlist('name', 'Adrian')
        d.appendlist('name', 'Simon')
        self.assertEqual(d.getlist('name'), ['Adrian', 'Simon'])

    def test_copy(self):
        for copy_func in [copy.copy, lambda d: d.copy()]:
            d1 = MultiValueDict({
                "developers": ["Carl", "Fred"]
            })
            self.assertEqual(d1["developers"], "Fred")
            d2 = copy_func(d1)
            d2.update({"developers": "Groucho"})
            self.assertEqual(d2["developers"], "Groucho")
            self.assertEqual(d1["developers"], "Fred")

            d1 = MultiValueDict({
                "key": [[]]
            })
            self.assertEqual(d1["key"], [])
            d2 = copy_func(d1)
            d2["key"].append("Penguin")
            self.assertEqual(d1["key"], ["Penguin"])
            self.assertEqual(d2["key"], ["Penguin"])

    def test_dict_translation(self):
        mvd = MultiValueDict({
            'devs': ['Bob', 'Joe'],
            'pm': ['Rory'],
        })
        d = mvd.dict()
        self.assertEqual(sorted(d), sorted(mvd))
        for key in mvd:
            self.assertEqual(d[key], mvd[key])

        self.assertEqual({}, MultiValueDict().dict())

    def test_getlist_doesnt_mutate(self):
        x = MultiValueDict({'a': ['1', '2'], 'b': ['3']})
        values = x.getlist('a')
        values += x.getlist('b')
        self.assertEqual(x.getlist('a'), ['1', '2'])

    def test_internal_getlist_does_mutate(self):
        x = MultiValueDict({'a': ['1', '2'], 'b': ['3']})
        values = x._getlist('a')
        values += x._getlist('b')
        self.assertEqual(x._getlist('a'), ['1', '2', '3'])

    def test_getlist_default(self):
        x = MultiValueDict({'a': [1]})
        MISSING = object()
        values = x.getlist('b', default=MISSING)
        self.assertIs(values, MISSING)

    def test_getlist_none_empty_values(self):
        x = MultiValueDict({'a': None, 'b': []})
        self.assertIsNone(x.getlist('a'))
        self.assertEqual(x.getlist('b'), [])


class ImmutableListTests(SimpleTestCase):

    def test_sort(self):
        d = ImmutableList(range(10))

        # AttributeError: ImmutableList object is immutable.
        with self.assertRaisesMessage(AttributeError, 'ImmutableList object is immutable.'):
            d.sort()

        self.assertEqual(repr(d), '(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)')

    def test_custom_warning(self):
        d = ImmutableList(range(10), warning="Object is immutable!")

        self.assertEqual(d[1], 1)

        # AttributeError: Object is immutable!
        with self.assertRaisesMessage(AttributeError, 'Object is immutable!'):
            d.__setitem__(1, 'test')


class DictWrapperTests(SimpleTestCase):

    def test_dictwrapper(self):
        def f(x):
            return "*%s" % x
        d = DictWrapper({'a': 'a'}, f, 'xx_')
        self.assertEqual(
            "Normal: %(a)s. Modified: %(xx_a)s" % d,
            'Normal: a. Modified: *a'
        )


class ImmutableCaseInsensitiveDictTests(SimpleTestCase):
    def setUp(self):
        self.dict_1 = ImmutableCaseInsensitiveDict({
            'Accept': 'application/json',
            'content-type': 'text/html'
        })

    def test_list(self):
        self.assertEqual(
            sorted(list(self.dict_1)),
            sorted(['Accept', 'content-type']))

    def test_dict(self):
        self.assertEqual(dict(self.dict_1), {
            'Accept': 'application/json',
            'content-type': 'text/html'
        })

    def test_repr(self):
        self.assertEqual(repr(self.dict_1), repr({
            'Accept': 'application/json',
            'content-type': 'text/html'
        }))

    def test_str(self):
        self.assertEqual(str(self.dict_1), str({
            'Accept': 'application/json',
            'content-type': 'text/html'
        }))

    def test_equals(self):
        self.assertTrue(self.dict_1 == {
            'Accept': 'application/json',
            'content-type': 'text/html'
        })

        self.assertTrue(self.dict_1 == {
            'accept': 'application/json',
            'Content-Type': 'text/html'
        })

    def test_items(self):
        other = {
            'Accept': 'application/json',
            'content-type': 'text/html'
        }
        self.assertEqual(list(self.dict_1.items()), list(other.items()))

    def test_copy(self):
        copy = self.dict_1.copy()

        # id(copy) != id(self.dict_1)
        self.assertIsNot(copy, self.dict_1)
        self.assertEqual(copy, self.dict_1)

    def test_getitem(self):
        self.assertEqual(self.dict_1['Accept'], 'application/json')
        self.assertEqual(self.dict_1['accept'], 'application/json')
        self.assertEqual(self.dict_1['aCCept'], 'application/json')

        self.assertEqual(self.dict_1['content-type'], 'text/html')
        self.assertEqual(self.dict_1['Content-Type'], 'text/html')
        self.assertEqual(self.dict_1['Content-type'], 'text/html')

    def test_membership(self):
        self.assertTrue('Accept' in self.dict_1)
        self.assertTrue('accept' in self.dict_1)
        self.assertTrue('aCCept' in self.dict_1)

        self.assertTrue('content-type' in self.dict_1)
        self.assertTrue('Content-Type' in self.dict_1)

    def test_delitem(self):
        "del should raise a TypeError because this is immutable"
        # Preconditions
        self.assertTrue('Accept' in self.dict_1)
        with self.assertRaises(TypeError):
            del self.dict_1['Accept']

        # Postconditions
        self.assertTrue('Accept' in self.dict_1)

    def test_setitem(self):
        "del should raise a TypeError because this is immutable"
        # Preconditions
        self.assertEqual(len(self.dict_1), 2)

        with self.assertRaises(TypeError):
            self.dict_1['New Key'] = 1

        # Postconditions
        self.assertEqual(len(self.dict_1), 2)


class EnvironHeadersTestCase(SimpleTestCase):
    def test_parse_cgi_headers_basics(self):
        parser = EnvironHeaders.parse_cgi_header

        self.assertEqual(parser('HTTP_ACCEPT'), 'Accept')
        self.assertEqual(parser('HTTP_HOST'), 'Host')
        self.assertEqual(parser('HTTP_USER_AGENT'), 'User-Agent')
        self.assertEqual(parser('HTTP_REFERER'), 'Referer')
        self.assertEqual(parser('HTTP_IF_MATCH'), 'If-Match')
        self.assertEqual(parser('HTTP_ACCEPT_ENCODING'), 'Accept-Encoding')
        self.assertEqual(parser('HTTP_COOKIE'), 'Cookie')

    def test_parse_cgi_headers_special_and_custom(self):
        parser = EnvironHeaders.parse_cgi_header

        self.assertEqual(parser('HTTP_X_PROTO'), 'X-Proto')
        self.assertEqual(parser('HTTP_X_FORWARDED_PROTO'), 'X-Forwarded-Proto')
        self.assertEqual(parser('HTTP_X_FORWARDED_HOST'), 'X-Forwarded-Host')
        self.assertEqual(parser('HTTP_X_FORWARDED_PORT'), 'X-Forwarded-Port')
        self.assertEqual(parser('HTTP_X_CUSTOM_HEADER_1'), 'X-Custom-Header-1')
        self.assertEqual(parser('HTTP_X_CUSTOM_HEADER_2'), 'X-Custom-Header-2')

    def test_parse_cgi_headers_cgi_exceptions_and_invalids(self):
        parser = EnvironHeaders.parse_cgi_header

        self.assertIsNone(parser('HTTP_CONTENT_TYPE'))
        self.assertIsNone(parser('HTTP_CONTENT_LENGTH'))

        self.assertEqual(parser('CONTENT_TYPE'), 'Content-Type')
        self.assertEqual(parser('CONTENT_LENGTH'), 'Content-Length')

    def test_basic_environ_special_cases_and_exceptions(self):
        environ = {
            'HTTP_CONTENT_TYPE': 'text/html',
            'HTTP_CONTENT_LENGTH': '100',
            'CONTENT_TYPE': 'text/html',
            'CONTENT_LENGTH': '100',
            'HTTP_ACCEPT': '*',
            'HTTP_HOST': 'example.com',
        }
        headers = EnvironHeaders(environ)
        expected = ['Accept', 'Content-Length', 'Content-Type', 'Host']

        self.assertEqual(sorted(headers), expected)

    def test_basic_valid_environ(self):
        environ = {
            'CONTENT_TYPE': 'text/html',
            'CONTENT_LENGTH': '100',
            'HTTP_ACCEPT': '*',
            'HTTP_HOST': 'example.com',
            'HTTP_USER_AGENT': 'python-requests/1.2.0',
            'HTTP_REFERER': 'https://docs.djangoproject.com',
            'HTTP_IF_MATCH': 'py7h0n',
            'HTTP_IF_NONE_MATCH': 'dj4n60',
            'HTTP_IF_MODIFIED_SINCE': 'Sat, 12 Feb 2011 17:38:44 GMT',
            'HTTP_ACCEPT_ENCODING': 'gzip, deflate, br',
            'HTTP_CONNECTION': 'keep-alive',
            'HTTP_PRAGMA': 'no-cache',
            'HTTP_CACHE_CONTROL': 'no-cache', 'HTTP_UPGRADE_INSECURE_REQUESTS': '1',
            'HTTP_ACCEPT_LANGUAGE': 'es-419,es;q=0.9,en;q=0.8,en-US;q=0.7',
            'HTTP_COOKIE': '%7B%22hello%22%3A%22world%22%7D;another=value'
        }
        headers = EnvironHeaders(environ)
        expected = [
            'Accept', 'Accept-Encoding', 'Accept-Language', 'Cache-Control',
            'Connection', 'Content-Length', 'Content-Type',
            'Cookie', 'Host', 'If-Match', 'If-Modified-Since', 'If-None-Match',
            'Pragma', 'Referer', 'Upgrade-Insecure-Requests', 'User-Agent']

        self.assertEqual(sorted(headers), expected)
        self.assertEqual(dict(headers), {
            'Content-Type': 'text/html',
            'Content-Length': '100',
            'Accept': '*',
            'Host': 'example.com',
            'User-Agent': 'python-requests/1.2.0',
            'Referer': 'https://docs.djangoproject.com',
            'If-Match': 'py7h0n',
            'If-None-Match': 'dj4n60',
            'If-Modified-Since': 'Sat, 12 Feb 2011 17:38:44 GMT',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Language': 'es-419,es;q=0.9,en;q=0.8,en-US;q=0.7',
            'Cookie': '%7B%22hello%22%3A%22world%22%7D;another=value'})

    def test_custom_and_special_services_headers(self):
        environ = {
            'CONTENT_TYPE': 'text/html',
            'CONTENT_LENGTH': '100',
            'HTTP_ACCEPT': '*',
            'HTTP_HOST': 'example.com',
            'HTTP_USER_AGENT': 'python-requests/1.2.0',

            # Special headers used by AWS and other services
            'HTTP_X_PROTO': 'https',
            'HTTP_X_FORWARDED_HOST': 'forward.com',
            'HTTP_X_FORWARDED_PORT': '80',
            'HTTP_X_FORWARDED_PROTOCOL': 'https',

            # Custom headers
            'HTTP_X_CUSTOM_HEADER_1': 'custom_header_1',
            'HTTP_X_CUSTOM_HEADER_2': 'custom_header_2',
        }
        headers = EnvironHeaders(environ)
        expected = [
            'Accept', 'Content-Length', 'Content-Type', 'Host', 'User-Agent',
            'X-Custom-Header-1', 'X-Custom-Header-2', 'X-Forwarded-Host',
            'X-Forwarded-Port', 'X-Forwarded-Protocol', 'X-Proto']

        self.assertEqual(sorted(headers), expected)

        self.assertEqual(dict(headers), {
            'Content-Type': 'text/html',
            'Content-Length': '100',
            'Accept': '*',
            'Host': 'example.com',
            'User-Agent': 'python-requests/1.2.0',
            'X-Proto': 'https',
            'X-Forwarded-Host': 'forward.com',
            'X-Forwarded-Port': '80',
            'X-Forwarded-Protocol': 'https',
            'X-Custom-Header-1': 'custom_header_1',
            'X-Custom-Header-2': 'custom_header_2'})

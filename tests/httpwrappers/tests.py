# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import copy
import json
import os
import pickle
import unittest
import uuid

from django.core.exceptions import SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder
from django.core.signals import request_finished
from django.db import close_old_connections
from django.http import (
    BadHeaderError, HttpResponse, HttpResponseNotAllowed,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, QueryDict, SimpleCookie,
    StreamingHttpResponse, parse_cookie,
)
from django.test import TestCase
from django.utils import six
from django.utils._os import upath
from django.utils.encoding import force_str, force_text, smart_str
from django.utils.functional import lazy

lazystr = lazy(force_text, six.text_type)


class QueryDictTests(unittest.TestCase):
    def test_create_with_no_args(self):
        self.assertEqual(QueryDict(), QueryDict(str('')))

    def test_missing_key(self):
        q = QueryDict()
        self.assertRaises(KeyError, q.__getitem__, 'foo')

    def test_immutability(self):
        q = QueryDict()
        self.assertRaises(AttributeError, q.__setitem__, 'something', 'bar')
        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar'])
        self.assertRaises(AttributeError, q.appendlist, 'foo', ['bar'])
        self.assertRaises(AttributeError, q.update, {'foo': 'bar'})
        self.assertRaises(AttributeError, q.pop, 'foo')
        self.assertRaises(AttributeError, q.popitem)
        self.assertRaises(AttributeError, q.clear)

    def test_immutable_get_with_default(self):
        q = QueryDict()
        self.assertEqual(q.get('foo', 'default'), 'default')

    def test_immutable_basic_operations(self):
        q = QueryDict()
        self.assertEqual(q.getlist('foo'), [])
        if six.PY2:
            self.assertEqual(q.has_key('foo'), False)
        self.assertEqual('foo' in q, False)
        self.assertEqual(list(six.iteritems(q)), [])
        self.assertEqual(list(six.iterlists(q)), [])
        self.assertEqual(list(six.iterkeys(q)), [])
        self.assertEqual(list(six.itervalues(q)), [])
        self.assertEqual(len(q), 0)
        self.assertEqual(q.urlencode(), '')

    def test_single_key_value(self):
        """Test QueryDict with one key/value pair"""

        q = QueryDict(str('foo=bar'))
        self.assertEqual(q['foo'], 'bar')
        self.assertRaises(KeyError, q.__getitem__, 'bar')
        self.assertRaises(AttributeError, q.__setitem__, 'something', 'bar')

        self.assertEqual(q.get('foo', 'default'), 'bar')
        self.assertEqual(q.get('bar', 'default'), 'default')
        self.assertEqual(q.getlist('foo'), ['bar'])
        self.assertEqual(q.getlist('bar'), [])

        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar'])
        self.assertRaises(AttributeError, q.appendlist, 'foo', ['bar'])

        if six.PY2:
            self.assertTrue(q.has_key('foo'))
        self.assertIn('foo', q)
        if six.PY2:
            self.assertFalse(q.has_key('bar'))
        self.assertNotIn('bar', q)

        self.assertEqual(list(six.iteritems(q)), [('foo', 'bar')])
        self.assertEqual(list(six.iterlists(q)), [('foo', ['bar'])])
        self.assertEqual(list(six.iterkeys(q)), ['foo'])
        self.assertEqual(list(six.itervalues(q)), ['bar'])
        self.assertEqual(len(q), 1)

        self.assertRaises(AttributeError, q.update, {'foo': 'bar'})
        self.assertRaises(AttributeError, q.pop, 'foo')
        self.assertRaises(AttributeError, q.popitem)
        self.assertRaises(AttributeError, q.clear)
        self.assertRaises(AttributeError, q.setdefault, 'foo', 'bar')

        self.assertEqual(q.urlencode(), 'foo=bar')

    def test_urlencode(self):
        q = QueryDict(mutable=True)
        q['next'] = '/a&b/'
        self.assertEqual(q.urlencode(), 'next=%2Fa%26b%2F')
        self.assertEqual(q.urlencode(safe='/'), 'next=/a%26b/')
        q = QueryDict(mutable=True)
        q['next'] = '/t\xebst&key/'
        self.assertEqual(q.urlencode(), 'next=%2Ft%C3%ABst%26key%2F')
        self.assertEqual(q.urlencode(safe='/'), 'next=/t%C3%ABst%26key/')

    def test_mutable_copy(self):
        """A copy of a QueryDict is mutable."""
        q = QueryDict().copy()
        self.assertRaises(KeyError, q.__getitem__, "foo")
        q['name'] = 'john'
        self.assertEqual(q['name'], 'john')

    def test_mutable_delete(self):
        q = QueryDict(mutable=True)
        q['name'] = 'john'
        del q['name']
        self.assertNotIn('name', q)

    def test_basic_mutable_operations(self):
        q = QueryDict(mutable=True)
        q['name'] = 'john'
        self.assertEqual(q.get('foo', 'default'), 'default')
        self.assertEqual(q.get('name', 'default'), 'john')
        self.assertEqual(q.getlist('name'), ['john'])
        self.assertEqual(q.getlist('foo'), [])

        q.setlist('foo', ['bar', 'baz'])
        self.assertEqual(q.get('foo', 'default'), 'baz')
        self.assertEqual(q.getlist('foo'), ['bar', 'baz'])

        q.appendlist('foo', 'another')
        self.assertEqual(q.getlist('foo'), ['bar', 'baz', 'another'])
        self.assertEqual(q['foo'], 'another')
        if six.PY2:
            self.assertTrue(q.has_key('foo'))
        self.assertIn('foo', q)

        self.assertListEqual(sorted(list(six.iteritems(q))),
                             [('foo', 'another'), ('name', 'john')])
        self.assertListEqual(sorted(list(six.iterlists(q))),
                             [('foo', ['bar', 'baz', 'another']), ('name', ['john'])])
        self.assertListEqual(sorted(list(six.iterkeys(q))),
                             ['foo', 'name'])
        self.assertListEqual(sorted(list(six.itervalues(q))),
                             ['another', 'john'])

        q.update({'foo': 'hello'})
        self.assertEqual(q['foo'], 'hello')
        self.assertEqual(q.get('foo', 'not available'), 'hello')
        self.assertEqual(q.getlist('foo'), ['bar', 'baz', 'another', 'hello'])
        self.assertEqual(q.pop('foo'), ['bar', 'baz', 'another', 'hello'])
        self.assertEqual(q.pop('foo', 'not there'), 'not there')
        self.assertEqual(q.get('foo', 'not there'), 'not there')
        self.assertEqual(q.setdefault('foo', 'bar'), 'bar')
        self.assertEqual(q['foo'], 'bar')
        self.assertEqual(q.getlist('foo'), ['bar'])
        self.assertIn(q.urlencode(), ['foo=bar&name=john', 'name=john&foo=bar'])

        q.clear()
        self.assertEqual(len(q), 0)

    def test_multiple_keys(self):
        """Test QueryDict with two key/value pairs with same keys."""

        q = QueryDict(str('vote=yes&vote=no'))

        self.assertEqual(q['vote'], 'no')
        self.assertRaises(AttributeError, q.__setitem__, 'something', 'bar')

        self.assertEqual(q.get('vote', 'default'), 'no')
        self.assertEqual(q.get('foo', 'default'), 'default')
        self.assertEqual(q.getlist('vote'), ['yes', 'no'])
        self.assertEqual(q.getlist('foo'), [])

        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar', 'baz'])
        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar', 'baz'])
        self.assertRaises(AttributeError, q.appendlist, 'foo', ['bar'])

        if six.PY2:
            self.assertEqual(q.has_key('vote'), True)
        self.assertEqual('vote' in q, True)
        if six.PY2:
            self.assertEqual(q.has_key('foo'), False)
        self.assertEqual('foo' in q, False)
        self.assertEqual(list(six.iteritems(q)), [('vote', 'no')])
        self.assertEqual(list(six.iterlists(q)), [('vote', ['yes', 'no'])])
        self.assertEqual(list(six.iterkeys(q)), ['vote'])
        self.assertEqual(list(six.itervalues(q)), ['no'])
        self.assertEqual(len(q), 1)

        self.assertRaises(AttributeError, q.update, {'foo': 'bar'})
        self.assertRaises(AttributeError, q.pop, 'foo')
        self.assertRaises(AttributeError, q.popitem)
        self.assertRaises(AttributeError, q.clear)
        self.assertRaises(AttributeError, q.setdefault, 'foo', 'bar')
        self.assertRaises(AttributeError, q.__delitem__, 'vote')

    if six.PY2:
        def test_invalid_input_encoding(self):
            """
            QueryDicts must be able to handle invalid input encoding (in this
            case, bad UTF-8 encoding), falling back to ISO-8859-1 decoding.

            This test doesn't apply under Python 3 because the URL is a string
            and not a bytestring.
            """
            q = QueryDict(str(b'foo=bar&foo=\xff'))
            self.assertEqual(q['foo'], '\xff')
            self.assertEqual(q.getlist('foo'), ['bar', '\xff'])

    def test_pickle(self):
        q = QueryDict()
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q == q1, True)
        q = QueryDict(str('a=b&c=d'))
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q == q1, True)
        q = QueryDict(str('a=b&c=d&a=1'))
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q == q1, True)

    def test_update_from_querydict(self):
        """Regression test for #8278: QueryDict.update(QueryDict)"""
        x = QueryDict(str("a=1&a=2"), mutable=True)
        y = QueryDict(str("a=3&a=4"))
        x.update(y)
        self.assertEqual(x.getlist('a'), ['1', '2', '3', '4'])

    def test_non_default_encoding(self):
        """#13572 - QueryDict with a non-default encoding"""
        q = QueryDict(str('cur=%A4'), encoding='iso-8859-15')
        self.assertEqual(q.encoding, 'iso-8859-15')
        self.assertEqual(list(six.iteritems(q)), [('cur', '€')])
        self.assertEqual(q.urlencode(), 'cur=%A4')
        q = q.copy()
        self.assertEqual(q.encoding, 'iso-8859-15')
        self.assertEqual(list(six.iteritems(q)), [('cur', '€')])
        self.assertEqual(q.urlencode(), 'cur=%A4')
        self.assertEqual(copy.copy(q).encoding, 'iso-8859-15')
        self.assertEqual(copy.deepcopy(q).encoding, 'iso-8859-15')


class HttpResponseTests(unittest.TestCase):

    def test_headers_type(self):
        r = HttpResponse()

        # The following tests explicitly test types in addition to values
        # because in Python 2 u'foo' == b'foo'.

        # ASCII unicode or bytes values are converted to native strings.
        r['key'] = 'test'
        self.assertEqual(r['key'], str('test'))
        self.assertIsInstance(r['key'], str)
        r['key'] = 'test'.encode('ascii')
        self.assertEqual(r['key'], str('test'))
        self.assertIsInstance(r['key'], str)
        self.assertIn(b'test', r.serialize_headers())

        # Latin-1 unicode or bytes values are also converted to native strings.
        r['key'] = 'café'
        self.assertEqual(r['key'], smart_str('café', 'latin-1'))
        self.assertIsInstance(r['key'], str)
        r['key'] = 'café'.encode('latin-1')
        self.assertEqual(r['key'], smart_str('café', 'latin-1'))
        self.assertIsInstance(r['key'], str)
        self.assertIn('café'.encode('latin-1'), r.serialize_headers())

        # Other unicode values are MIME-encoded (there's no way to pass them as bytes).
        r['key'] = '†'
        self.assertEqual(r['key'], str('=?utf-8?b?4oCg?='))
        self.assertIsInstance(r['key'], str)
        self.assertIn(b'=?utf-8?b?4oCg?=', r.serialize_headers())

        # The response also converts unicode or bytes keys to strings, but requires
        # them to contain ASCII
        r = HttpResponse()
        del r['Content-Type']
        r['foo'] = 'bar'
        l = list(r.items())
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0], ('foo', 'bar'))
        self.assertIsInstance(l[0][0], str)

        r = HttpResponse()
        del r['Content-Type']
        r[b'foo'] = 'bar'
        l = list(r.items())
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0], ('foo', 'bar'))
        self.assertIsInstance(l[0][0], str)

        r = HttpResponse()
        self.assertRaises(UnicodeError, r.__setitem__, 'føø', 'bar')
        self.assertRaises(UnicodeError, r.__setitem__, 'føø'.encode('utf-8'), 'bar')

    def test_long_line(self):
        # Bug #20889: long lines trigger newlines to be added to headers
        # (which is not allowed due to bug #10188)
        h = HttpResponse()
        f = 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz a\xcc\x88'.encode('latin-1')
        f = f.decode('utf-8')
        h['Content-Disposition'] = 'attachment; filename="%s"' % f
        # This one is triggering http://bugs.python.org/issue20747, that is Python
        # will itself insert a newline in the header
        h['Content-Disposition'] = 'attachment; filename="EdelRot_Blu\u0308te (3)-0.JPG"'

    def test_newlines_in_headers(self):
        # Bug #10188: Do not allow newlines in headers (CR or LF)
        r = HttpResponse()
        self.assertRaises(BadHeaderError, r.__setitem__, 'test\rstr', 'test')
        self.assertRaises(BadHeaderError, r.__setitem__, 'test\nstr', 'test')

    def test_dict_behavior(self):
        """
        Test for bug #14020: Make HttpResponse.get work like dict.get
        """
        r = HttpResponse()
        self.assertEqual(r.get('test'), None)

    def test_non_string_content(self):
        # Bug 16494: HttpResponse should behave consistently with non-strings
        r = HttpResponse(12345)
        self.assertEqual(r.content, b'12345')

        # test content via property
        r = HttpResponse()
        r.content = 12345
        self.assertEqual(r.content, b'12345')

    def test_iter_content(self):
        r = HttpResponse(['abc', 'def', 'ghi'])
        self.assertEqual(r.content, b'abcdefghi')

        # test iter content via property
        r = HttpResponse()
        r.content = ['idan', 'alex', 'jacob']
        self.assertEqual(r.content, b'idanalexjacob')

        r = HttpResponse()
        r.content = [1, 2, 3]
        self.assertEqual(r.content, b'123')

        # test odd inputs
        r = HttpResponse()
        r.content = ['1', '2', 3, '\u079e']
        # '\xde\x9e' == unichr(1950).encode('utf-8')
        self.assertEqual(r.content, b'123\xde\x9e')

        # .content can safely be accessed multiple times.
        r = HttpResponse(iter(['hello', 'world']))
        self.assertEqual(r.content, r.content)
        self.assertEqual(r.content, b'helloworld')
        # __iter__ can safely be called multiple times (#20187).
        self.assertEqual(b''.join(r), b'helloworld')
        self.assertEqual(b''.join(r), b'helloworld')
        # Accessing .content still works.
        self.assertEqual(r.content, b'helloworld')

        # Accessing .content also works if the response was iterated first.
        r = HttpResponse(iter(['hello', 'world']))
        self.assertEqual(b''.join(r), b'helloworld')
        self.assertEqual(r.content, b'helloworld')

        # Additional content can be written to the response.
        r = HttpResponse(iter(['hello', 'world']))
        self.assertEqual(r.content, b'helloworld')
        r.write('!')
        self.assertEqual(r.content, b'helloworld!')

    def test_iterator_isnt_rewound(self):
        # Regression test for #13222
        r = HttpResponse('abc')
        i = iter(r)
        self.assertEqual(list(i), [b'abc'])
        self.assertEqual(list(i), [])

    def test_lazy_content(self):
        r = HttpResponse(lazystr('helloworld'))
        self.assertEqual(r.content, b'helloworld')

    def test_file_interface(self):
        r = HttpResponse()
        r.write(b"hello")
        self.assertEqual(r.tell(), 5)
        r.write("привет")
        self.assertEqual(r.tell(), 17)

        r = HttpResponse(['abc'])
        r.write('def')
        self.assertEqual(r.tell(), 6)
        self.assertEqual(r.content, b'abcdef')

        # with Content-Encoding header
        r = HttpResponse()
        r['Content-Encoding'] = 'winning'
        r.write(b'abc')
        r.write(b'def')
        self.assertEqual(r.content, b'abcdef')

    def test_stream_interface(self):
        r = HttpResponse('asdf')
        self.assertEqual(r.getvalue(), b'asdf')

        r = HttpResponse()
        self.assertEqual(r.writable(), True)
        r.writelines(['foo\n', 'bar\n', 'baz\n'])
        self.assertEqual(r.content, b'foo\nbar\nbaz\n')

    def test_unsafe_redirect(self):
        bad_urls = [
            'data:text/html,<script>window.alert("xss")</script>',
            'mailto:test@example.com',
            'file:///etc/passwd',
        ]
        for url in bad_urls:
            self.assertRaises(SuspiciousOperation,
                              HttpResponseRedirect, url)
            self.assertRaises(SuspiciousOperation,
                              HttpResponsePermanentRedirect, url)


class HttpResponseSubclassesTests(TestCase):
    def test_redirect(self):
        response = HttpResponseRedirect('/redirected/')
        self.assertEqual(response.status_code, 302)
        # Test that standard HttpResponse init args can be used
        response = HttpResponseRedirect('/redirected/',
            content='The resource has temporarily moved',
            content_type='text/html')
        self.assertContains(response, 'The resource has temporarily moved', status_code=302)
        # Test that url attribute is right
        self.assertEqual(response.url, response['Location'])

    def test_redirect_lazy(self):
        """Make sure HttpResponseRedirect works with lazy strings."""
        r = HttpResponseRedirect(lazystr('/redirected/'))
        self.assertEqual(r.url, '/redirected/')

    def test_not_modified(self):
        response = HttpResponseNotModified()
        self.assertEqual(response.status_code, 304)
        # 304 responses should not have content/content-type
        with self.assertRaises(AttributeError):
            response.content = "Hello dear"
        self.assertNotIn('content-type', response)

    def test_not_allowed(self):
        response = HttpResponseNotAllowed(['GET'])
        self.assertEqual(response.status_code, 405)
        # Test that standard HttpResponse init args can be used
        response = HttpResponseNotAllowed(['GET'],
            content='Only the GET method is allowed',
            content_type='text/html')
        self.assertContains(response, 'Only the GET method is allowed', status_code=405)


class JsonResponseTests(TestCase):
    def test_json_response_non_ascii(self):
        data = {'key': 'łóżko'}
        response = JsonResponse(data)
        self.assertEqual(json.loads(response.content.decode()), data)

    def test_json_response_raises_type_error_with_default_setting(self):
        with self.assertRaisesMessage(TypeError,
                'In order to allow non-dict objects to be serialized set the '
                'safe parameter to False'):
            JsonResponse([1, 2, 3])

    def test_json_response_text(self):
        response = JsonResponse('foobar', safe=False)
        self.assertEqual(json.loads(response.content.decode()), 'foobar')

    def test_json_response_list(self):
        response = JsonResponse(['foo', 'bar'], safe=False)
        self.assertEqual(json.loads(response.content.decode()), ['foo', 'bar'])

    def test_json_response_uuid(self):
        u = uuid.uuid4()
        response = JsonResponse(u, safe=False)
        self.assertEqual(json.loads(response.content.decode()), str(u))

    def test_json_response_custom_encoder(self):
        class CustomDjangoJSONEncoder(DjangoJSONEncoder):
            def encode(self, o):
                return json.dumps({'foo': 'bar'})

        response = JsonResponse({}, encoder=CustomDjangoJSONEncoder)
        self.assertEqual(json.loads(response.content.decode()), {'foo': 'bar'})


class StreamingHttpResponseTests(TestCase):
    def test_streaming_response(self):
        r = StreamingHttpResponse(iter(['hello', 'world']))

        # iterating over the response itself yields bytestring chunks.
        chunks = list(r)
        self.assertEqual(chunks, [b'hello', b'world'])
        for chunk in chunks:
            self.assertIsInstance(chunk, six.binary_type)

        # and the response can only be iterated once.
        self.assertEqual(list(r), [])

        # even when a sequence that can be iterated many times, like a list,
        # is given as content.
        r = StreamingHttpResponse(['abc', 'def'])
        self.assertEqual(list(r), [b'abc', b'def'])
        self.assertEqual(list(r), [])

        # iterating over Unicode strings still yields bytestring chunks.
        r.streaming_content = iter(['hello', 'café'])
        chunks = list(r)
        # '\xc3\xa9' == unichr(233).encode('utf-8')
        self.assertEqual(chunks, [b'hello', b'caf\xc3\xa9'])
        for chunk in chunks:
            self.assertIsInstance(chunk, six.binary_type)

        # streaming responses don't have a `content` attribute.
        self.assertFalse(hasattr(r, 'content'))

        # and you can't accidentally assign to a `content` attribute.
        with self.assertRaises(AttributeError):
            r.content = 'xyz'

        # but they do have a `streaming_content` attribute.
        self.assertTrue(hasattr(r, 'streaming_content'))

        # that exists so we can check if a response is streaming, and wrap or
        # replace the content iterator.
        r.streaming_content = iter(['abc', 'def'])
        r.streaming_content = (chunk.upper() for chunk in r.streaming_content)
        self.assertEqual(list(r), [b'ABC', b'DEF'])

        # coercing a streaming response to bytes doesn't return a complete HTTP
        # message like a regular response does. it only gives us the headers.
        r = StreamingHttpResponse(iter(['hello', 'world']))
        self.assertEqual(
            six.binary_type(r), b'Content-Type: text/html; charset=utf-8')

        # and this won't consume its content.
        self.assertEqual(list(r), [b'hello', b'world'])

        # additional content cannot be written to the response.
        r = StreamingHttpResponse(iter(['hello', 'world']))
        with self.assertRaises(Exception):
            r.write('!')

        # and we can't tell the current position.
        with self.assertRaises(Exception):
            r.tell()

        r = StreamingHttpResponse(iter(['hello', 'world']))
        self.assertEqual(r.getvalue(), b'helloworld')


class FileCloseTests(TestCase):

    def setUp(self):
        # Disable the request_finished signal during this test
        # to avoid interfering with the database connection.
        request_finished.disconnect(close_old_connections)

    def tearDown(self):
        request_finished.connect(close_old_connections)

    def test_response(self):
        filename = os.path.join(os.path.dirname(upath(__file__)), 'abc.txt')

        # file isn't closed until we close the response.
        file1 = open(filename)
        r = HttpResponse(file1)
        self.assertFalse(file1.closed)
        r.close()
        self.assertTrue(file1.closed)

        # don't automatically close file when we finish iterating the response.
        file1 = open(filename)
        r = HttpResponse(file1)
        self.assertFalse(file1.closed)
        list(r)
        self.assertFalse(file1.closed)
        r.close()
        self.assertTrue(file1.closed)

        # when multiple file are assigned as content, make sure they are all
        # closed with the response.
        file1 = open(filename)
        file2 = open(filename)
        r = HttpResponse(file1)
        r.content = file2
        self.assertFalse(file1.closed)
        self.assertFalse(file2.closed)
        r.close()
        self.assertTrue(file1.closed)
        self.assertTrue(file2.closed)

    def test_streaming_response(self):
        filename = os.path.join(os.path.dirname(upath(__file__)), 'abc.txt')

        # file isn't closed until we close the response.
        file1 = open(filename)
        r = StreamingHttpResponse(file1)
        self.assertFalse(file1.closed)
        r.close()
        self.assertTrue(file1.closed)

        # when multiple file are assigned as content, make sure they are all
        # closed with the response.
        file1 = open(filename)
        file2 = open(filename)
        r = StreamingHttpResponse(file1)
        r.streaming_content = file2
        self.assertFalse(file1.closed)
        self.assertFalse(file2.closed)
        r.close()
        self.assertTrue(file1.closed)
        self.assertTrue(file2.closed)


class CookieTests(unittest.TestCase):
    def test_encode(self):
        """
        Test that we don't output tricky characters in encoded value
        """
        c = SimpleCookie()
        c['test'] = "An,awkward;value"
        self.assertNotIn(";", c.output().rstrip(';'))  # IE compat
        self.assertNotIn(",", c.output().rstrip(';'))  # Safari compat

    def test_decode(self):
        """
        Test that we can still preserve semi-colons and commas
        """
        c = SimpleCookie()
        c['test'] = "An,awkward;value"
        c2 = SimpleCookie()
        c2.load(c.output()[12:])
        self.assertEqual(c['test'].value, c2['test'].value)
        c3 = parse_cookie(c.output()[12:])
        self.assertEqual(c['test'].value, c3['test'])

    def test_decode_2(self):
        """
        Test that we haven't broken normal encoding
        """
        c = SimpleCookie()
        c['test'] = b"\xf0"
        c2 = SimpleCookie()
        c2.load(c.output()[12:])
        self.assertEqual(c['test'].value, c2['test'].value)
        c3 = parse_cookie(c.output()[12:])
        self.assertEqual(c['test'].value, c3['test'])

    def test_nonstandard_keys(self):
        """
        Test that a single non-standard cookie name doesn't affect all cookies. Ticket #13007.
        """
        self.assertIn('good_cookie', parse_cookie('good_cookie=yes;bad:cookie=yes').keys())

    def test_repeated_nonstandard_keys(self):
        """
        Test that a repeated non-standard name doesn't affect all cookies. Ticket #15852
        """
        self.assertIn('good_cookie', parse_cookie('a:=b; a:=c; good_cookie=yes').keys())

    def test_python_cookies(self):
        """
        Test cases copied from Python's Lib/test/test_http_cookies.py
        """
        self.assertEqual(parse_cookie('chips=ahoy; vienna=finger'), {'chips': 'ahoy', 'vienna': 'finger'})
        # Here parse_cookie() differs from Python's cookie parsing in that it
        # treats all semicolons as delimiters, even within quotes.
        self.assertEqual(
            parse_cookie('keebler="E=mc2; L=\\"Loves\\"; fudge=\\012;"'),
            {'keebler': '"E=mc2', 'L': '\\"Loves\\"', 'fudge': '\\012', '': '"'}
        )
        # Illegal cookies that have an '=' char in an unquoted value.
        self.assertEqual(parse_cookie('keebler=E=mc2'), {'keebler': 'E=mc2'})
        # Cookies with ':' character in their name.
        self.assertEqual(parse_cookie('key:term=value:term'), {'key:term': 'value:term'})
        # Cookies with '[' and ']'.
        self.assertEqual(parse_cookie('a=b; c=[; d=r; f=h'), {'a': 'b', 'c': '[', 'd': 'r', 'f': 'h'})

    def test_cookie_edgecases(self):
        # Cookies that RFC6265 allows.
        self.assertEqual(parse_cookie('a=b; Domain=example.com'), {'a': 'b', 'Domain': 'example.com'})
        # parse_cookie() has historically kept only the last cookie with the
        # same name.
        self.assertEqual(parse_cookie('a=b; h=i; a=c'), {'a': 'c', 'h': 'i'})

    def test_invalid_cookies(self):
        """
        Cookie strings that go against RFC6265 but browsers will send if set
        via document.cookie.
        """
        # Chunks without an equals sign appear as unnamed values per
        # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
        self.assertIn('django_language', parse_cookie('abc=def; unnamed; django_language=en').keys())
        # Even a double quote may be an unamed value.
        self.assertEqual(parse_cookie('a=b; "; c=d'), {'a': 'b', '': '"', 'c': 'd'})
        # Spaces in names and values, and an equals sign in values.
        self.assertEqual(parse_cookie('a b c=d e = f; gh=i'), {'a b c': 'd e = f', 'gh': 'i'})
        # More characters the spec forbids.
        self.assertEqual(parse_cookie('a   b,c<>@:/[]?{}=d  "  =e,f g'), {'a   b,c<>@:/[]?{}': 'd  "  =e,f g'})
        # Unicode characters. The spec only allows ASCII.
        self.assertEqual(parse_cookie('saint=André Bessette'), {'saint': force_str('André Bessette')})
        # Browsers don't send extra whitespace or semicolons in Cookie headers,
        # but parse_cookie() should parse whitespace the same way
        # document.cookie parses whitespace.
        self.assertEqual(parse_cookie('  =  b  ;  ;  =  ;   c  =  ;  '), {'': 'b', 'c': ''})

    def test_httponly_after_load(self):
        """
        Test that we can use httponly attribute on cookies that we load
        """
        c = SimpleCookie()
        c.load("name=val")
        c['name']['httponly'] = True
        self.assertTrue(c['name']['httponly'])

    def test_load_dict(self):
        c = SimpleCookie()
        c.load({'name': 'val'})
        self.assertEqual(c['name'].value, 'val')

    @unittest.skipUnless(six.PY2, "PY3 throws an exception on invalid cookie keys.")
    def test_bad_cookie(self):
        """
        Regression test for #18403
        """
        r = HttpResponse()
        r.set_cookie("a:.b/", 1)
        self.assertEqual(len(r.cookies.bad_cookies), 1)

    def test_pickle(self):
        rawdata = 'Customer="WILE_E_COYOTE"; Path=/acme; Version=1'
        expected_output = 'Set-Cookie: %s' % rawdata

        C = SimpleCookie()
        C.load(rawdata)
        self.assertEqual(C.output(), expected_output)

        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            C1 = pickle.loads(pickle.dumps(C, protocol=proto))
            self.assertEqual(C1.output(), expected_output)

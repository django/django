import copy
import json
import os
import pickle
import unittest
import uuid

from django.core.exceptions import DisallowedRedirect
from django.core.serializers.json import DjangoJSONEncoder
from django.core.signals import request_finished
from django.db import close_old_connections
from django.http import (
    BadHeaderError,
    HttpResponse,
    HttpResponseNotAllowed,
    HttpResponseNotModified,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    JsonResponse,
    QueryDict,
    SimpleCookie,
    StreamingHttpResponse,
    parse_cookie,
)
from django.test import SimpleTestCase
from django.utils.functional import lazystr


class QueryDictTests(SimpleTestCase):
    def test_create_with_no_args(self):
        self.assertEqual(QueryDict(), QueryDict(""))

    def test_missing_key(self):
        q = QueryDict()
        with self.assertRaises(KeyError):
            q.__getitem__("foo")

    def test_immutability(self):
        q = QueryDict()
        with self.assertRaises(AttributeError):
            q.__setitem__("something", "bar")
        with self.assertRaises(AttributeError):
            q.setlist("foo", ["bar"])
        with self.assertRaises(AttributeError):
            q.appendlist("foo", ["bar"])
        with self.assertRaises(AttributeError):
            q.update({"foo": "bar"})
        with self.assertRaises(AttributeError):
            q.pop("foo")
        with self.assertRaises(AttributeError):
            q.popitem()
        with self.assertRaises(AttributeError):
            q.clear()

    def test_immutable_get_with_default(self):
        q = QueryDict()
        self.assertEqual(q.get("foo", "default"), "default")

    def test_immutable_basic_operations(self):
        q = QueryDict()
        self.assertEqual(q.getlist("foo"), [])
        self.assertNotIn("foo", q)
        self.assertEqual(list(q), [])
        self.assertEqual(list(q.items()), [])
        self.assertEqual(list(q.lists()), [])
        self.assertEqual(list(q.keys()), [])
        self.assertEqual(list(q.values()), [])
        self.assertEqual(len(q), 0)
        self.assertEqual(q.urlencode(), "")

    def test_single_key_value(self):
        """Test QueryDict with one key/value pair"""

        q = QueryDict("foo=bar")
        self.assertEqual(q["foo"], "bar")
        with self.assertRaises(KeyError):
            q.__getitem__("bar")
        with self.assertRaises(AttributeError):
            q.__setitem__("something", "bar")

        self.assertEqual(q.get("foo", "default"), "bar")
        self.assertEqual(q.get("bar", "default"), "default")
        self.assertEqual(q.getlist("foo"), ["bar"])
        self.assertEqual(q.getlist("bar"), [])

        with self.assertRaises(AttributeError):
            q.setlist("foo", ["bar"])
        with self.assertRaises(AttributeError):
            q.appendlist("foo", ["bar"])

        self.assertIn("foo", q)
        self.assertNotIn("bar", q)

        self.assertEqual(list(q), ["foo"])
        self.assertEqual(list(q.items()), [("foo", "bar")])
        self.assertEqual(list(q.lists()), [("foo", ["bar"])])
        self.assertEqual(list(q.keys()), ["foo"])
        self.assertEqual(list(q.values()), ["bar"])
        self.assertEqual(len(q), 1)

        with self.assertRaises(AttributeError):
            q.update({"foo": "bar"})
        with self.assertRaises(AttributeError):
            q.pop("foo")
        with self.assertRaises(AttributeError):
            q.popitem()
        with self.assertRaises(AttributeError):
            q.clear()
        with self.assertRaises(AttributeError):
            q.setdefault("foo", "bar")

        self.assertEqual(q.urlencode(), "foo=bar")

    def test_urlencode(self):
        q = QueryDict(mutable=True)
        q["next"] = "/a&b/"
        self.assertEqual(q.urlencode(), "next=%2Fa%26b%2F")
        self.assertEqual(q.urlencode(safe="/"), "next=/a%26b/")
        q = QueryDict(mutable=True)
        q["next"] = "/t\xebst&key/"
        self.assertEqual(q.urlencode(), "next=%2Ft%C3%ABst%26key%2F")
        self.assertEqual(q.urlencode(safe="/"), "next=/t%C3%ABst%26key/")

    def test_urlencode_int(self):
        # Normally QueryDict doesn't contain non-string values but lazily
        # written tests may make that mistake.
        q = QueryDict(mutable=True)
        q["a"] = 1
        self.assertEqual(q.urlencode(), "a=1")

    def test_mutable_copy(self):
        """A copy of a QueryDict is mutable."""
        q = QueryDict().copy()
        with self.assertRaises(KeyError):
            q.__getitem__("foo")
        q["name"] = "john"
        self.assertEqual(q["name"], "john")

    def test_mutable_delete(self):
        q = QueryDict(mutable=True)
        q["name"] = "john"
        del q["name"]
        self.assertNotIn("name", q)

    def test_basic_mutable_operations(self):
        q = QueryDict(mutable=True)
        q["name"] = "john"
        self.assertEqual(q.get("foo", "default"), "default")
        self.assertEqual(q.get("name", "default"), "john")
        self.assertEqual(q.getlist("name"), ["john"])
        self.assertEqual(q.getlist("foo"), [])

        q.setlist("foo", ["bar", "baz"])
        self.assertEqual(q.get("foo", "default"), "baz")
        self.assertEqual(q.getlist("foo"), ["bar", "baz"])

        q.appendlist("foo", "another")
        self.assertEqual(q.getlist("foo"), ["bar", "baz", "another"])
        self.assertEqual(q["foo"], "another")
        self.assertIn("foo", q)

        self.assertCountEqual(q, ["foo", "name"])
        self.assertCountEqual(q.items(), [("foo", "another"), ("name", "john")])
        self.assertCountEqual(
            q.lists(), [("foo", ["bar", "baz", "another"]), ("name", ["john"])]
        )
        self.assertCountEqual(q.keys(), ["foo", "name"])
        self.assertCountEqual(q.values(), ["another", "john"])

        q.update({"foo": "hello"})
        self.assertEqual(q["foo"], "hello")
        self.assertEqual(q.get("foo", "not available"), "hello")
        self.assertEqual(q.getlist("foo"), ["bar", "baz", "another", "hello"])
        self.assertEqual(q.pop("foo"), ["bar", "baz", "another", "hello"])
        self.assertEqual(q.pop("foo", "not there"), "not there")
        self.assertEqual(q.get("foo", "not there"), "not there")
        self.assertEqual(q.setdefault("foo", "bar"), "bar")
        self.assertEqual(q["foo"], "bar")
        self.assertEqual(q.getlist("foo"), ["bar"])
        self.assertIn(q.urlencode(), ["foo=bar&name=john", "name=john&foo=bar"])

        q.clear()
        self.assertEqual(len(q), 0)

    def test_multiple_keys(self):
        """Test QueryDict with two key/value pairs with same keys."""

        q = QueryDict("vote=yes&vote=no")

        self.assertEqual(q["vote"], "no")
        with self.assertRaises(AttributeError):
            q.__setitem__("something", "bar")

        self.assertEqual(q.get("vote", "default"), "no")
        self.assertEqual(q.get("foo", "default"), "default")
        self.assertEqual(q.getlist("vote"), ["yes", "no"])
        self.assertEqual(q.getlist("foo"), [])

        with self.assertRaises(AttributeError):
            q.setlist("foo", ["bar", "baz"])
        with self.assertRaises(AttributeError):
            q.setlist("foo", ["bar", "baz"])
        with self.assertRaises(AttributeError):
            q.appendlist("foo", ["bar"])

        self.assertIn("vote", q)
        self.assertNotIn("foo", q)
        self.assertEqual(list(q), ["vote"])
        self.assertEqual(list(q.items()), [("vote", "no")])
        self.assertEqual(list(q.lists()), [("vote", ["yes", "no"])])
        self.assertEqual(list(q.keys()), ["vote"])
        self.assertEqual(list(q.values()), ["no"])
        self.assertEqual(len(q), 1)

        with self.assertRaises(AttributeError):
            q.update({"foo": "bar"})
        with self.assertRaises(AttributeError):
            q.pop("foo")
        with self.assertRaises(AttributeError):
            q.popitem()
        with self.assertRaises(AttributeError):
            q.clear()
        with self.assertRaises(AttributeError):
            q.setdefault("foo", "bar")
        with self.assertRaises(AttributeError):
            q.__delitem__("vote")

    def test_pickle(self):
        q = QueryDict()
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q, q1)
        q = QueryDict("a=b&c=d")
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q, q1)
        q = QueryDict("a=b&c=d&a=1")
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q, q1)

    def test_update_from_querydict(self):
        """Regression test for #8278: QueryDict.update(QueryDict)"""
        x = QueryDict("a=1&a=2", mutable=True)
        y = QueryDict("a=3&a=4")
        x.update(y)
        self.assertEqual(x.getlist("a"), ["1", "2", "3", "4"])

    def test_non_default_encoding(self):
        """#13572 - QueryDict with a non-default encoding"""
        q = QueryDict("cur=%A4", encoding="iso-8859-15")
        self.assertEqual(q.encoding, "iso-8859-15")
        self.assertEqual(list(q.items()), [("cur", "€")])
        self.assertEqual(q.urlencode(), "cur=%A4")
        q = q.copy()
        self.assertEqual(q.encoding, "iso-8859-15")
        self.assertEqual(list(q.items()), [("cur", "€")])
        self.assertEqual(q.urlencode(), "cur=%A4")
        self.assertEqual(copy.copy(q).encoding, "iso-8859-15")
        self.assertEqual(copy.deepcopy(q).encoding, "iso-8859-15")

    def test_querydict_fromkeys(self):
        self.assertEqual(
            QueryDict.fromkeys(["key1", "key2", "key3"]), QueryDict("key1&key2&key3")
        )

    def test_fromkeys_with_nonempty_value(self):
        self.assertEqual(
            QueryDict.fromkeys(["key1", "key2", "key3"], value="val"),
            QueryDict("key1=val&key2=val&key3=val"),
        )

    def test_fromkeys_is_immutable_by_default(self):
        # Match behavior of __init__() which is also immutable by default.
        q = QueryDict.fromkeys(["key1", "key2", "key3"])
        with self.assertRaisesMessage(
            AttributeError, "This QueryDict instance is immutable"
        ):
            q["key4"] = "nope"

    def test_fromkeys_mutable_override(self):
        q = QueryDict.fromkeys(["key1", "key2", "key3"], mutable=True)
        q["key4"] = "yep"
        self.assertEqual(q, QueryDict("key1&key2&key3&key4=yep"))

    def test_duplicates_in_fromkeys_iterable(self):
        self.assertEqual(QueryDict.fromkeys("xyzzy"), QueryDict("x&y&z&z&y"))

    def test_fromkeys_with_nondefault_encoding(self):
        key_utf16 = b"\xff\xfe\x8e\x02\xdd\x01\x9e\x02"
        value_utf16 = b"\xff\xfe\xdd\x01n\x00l\x00P\x02\x8c\x02"
        q = QueryDict.fromkeys([key_utf16], value=value_utf16, encoding="utf-16")
        expected = QueryDict("", mutable=True)
        expected["ʎǝʞ"] = "ǝnlɐʌ"
        self.assertEqual(q, expected)

    def test_fromkeys_empty_iterable(self):
        self.assertEqual(QueryDict.fromkeys([]), QueryDict(""))

    def test_fromkeys_noniterable(self):
        with self.assertRaises(TypeError):
            QueryDict.fromkeys(0)


class HttpResponseTests(SimpleTestCase):
    def test_headers_type(self):
        r = HttpResponse()

        # ASCII strings or bytes values are converted to strings.
        r.headers["key"] = "test"
        self.assertEqual(r.headers["key"], "test")
        r.headers["key"] = b"test"
        self.assertEqual(r.headers["key"], "test")
        self.assertIn(b"test", r.serialize_headers())

        # Non-ASCII values are serialized to Latin-1.
        r.headers["key"] = "café"
        self.assertIn("café".encode("latin-1"), r.serialize_headers())

        # Other Unicode values are MIME-encoded (there's no way to pass them as
        # bytes).
        r.headers["key"] = "†"
        self.assertEqual(r.headers["key"], "=?utf-8?b?4oCg?=")
        self.assertIn(b"=?utf-8?b?4oCg?=", r.serialize_headers())

        # The response also converts string or bytes keys to strings, but requires
        # them to contain ASCII
        r = HttpResponse()
        del r.headers["Content-Type"]
        r.headers["foo"] = "bar"
        headers = list(r.headers.items())
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], ("foo", "bar"))

        r = HttpResponse()
        del r.headers["Content-Type"]
        r.headers[b"foo"] = "bar"
        headers = list(r.headers.items())
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], ("foo", "bar"))
        self.assertIsInstance(headers[0][0], str)

        r = HttpResponse()
        with self.assertRaises(UnicodeError):
            r.headers.__setitem__("føø", "bar")
        with self.assertRaises(UnicodeError):
            r.headers.__setitem__("føø".encode(), "bar")

    def test_long_line(self):
        # Bug #20889: long lines trigger newlines to be added to headers
        # (which is not allowed due to bug #10188)
        h = HttpResponse()
        f = b"zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz a\xcc\x88"
        f = f.decode("utf-8")
        h.headers["Content-Disposition"] = 'attachment; filename="%s"' % f
        # This one is triggering https://bugs.python.org/issue20747, that is Python
        # will itself insert a newline in the header
        h.headers[
            "Content-Disposition"
        ] = 'attachment; filename="EdelRot_Blu\u0308te (3)-0.JPG"'

    def test_newlines_in_headers(self):
        # Bug #10188: Do not allow newlines in headers (CR or LF)
        r = HttpResponse()
        with self.assertRaises(BadHeaderError):
            r.headers.__setitem__("test\rstr", "test")
        with self.assertRaises(BadHeaderError):
            r.headers.__setitem__("test\nstr", "test")

    def test_encoded_with_newlines_in_headers(self):
        """
        Keys & values which throw a UnicodeError when encoding/decoding should
        still be checked for newlines and re-raised as a BadHeaderError.
        These specifically would still throw BadHeaderError after decoding
        successfully, because the newlines are sandwiched in the middle of the
        string and email.Header leaves those as they are.
        """
        r = HttpResponse()
        pairs = (
            ("†\nother", "test"),
            ("test", "†\nother"),
            (b"\xe2\x80\xa0\nother", "test"),
            ("test", b"\xe2\x80\xa0\nother"),
        )
        msg = "Header values can't contain newlines"
        for key, value in pairs:
            with self.subTest(key=key, value=value):
                with self.assertRaisesMessage(BadHeaderError, msg):
                    r[key] = value

    def test_dict_behavior(self):
        """
        Test for bug #14020: Make HttpResponse.get work like dict.get
        """
        r = HttpResponse()
        self.assertIsNone(r.get("test"))

    def test_non_string_content(self):
        # Bug 16494: HttpResponse should behave consistently with non-strings
        r = HttpResponse(12345)
        self.assertEqual(r.content, b"12345")

        # test content via property
        r = HttpResponse()
        r.content = 12345
        self.assertEqual(r.content, b"12345")

    def test_memoryview_content(self):
        r = HttpResponse(memoryview(b"memoryview"))
        self.assertEqual(r.content, b"memoryview")

    def test_iter_content(self):
        r = HttpResponse(["abc", "def", "ghi"])
        self.assertEqual(r.content, b"abcdefghi")

        # test iter content via property
        r = HttpResponse()
        r.content = ["idan", "alex", "jacob"]
        self.assertEqual(r.content, b"idanalexjacob")

        r = HttpResponse()
        r.content = [1, 2, 3]
        self.assertEqual(r.content, b"123")

        # test odd inputs
        r = HttpResponse()
        r.content = ["1", "2", 3, "\u079e"]
        # '\xde\x9e' == unichr(1950).encode()
        self.assertEqual(r.content, b"123\xde\x9e")

        # .content can safely be accessed multiple times.
        r = HttpResponse(iter(["hello", "world"]))
        self.assertEqual(r.content, r.content)
        self.assertEqual(r.content, b"helloworld")
        # __iter__ can safely be called multiple times (#20187).
        self.assertEqual(b"".join(r), b"helloworld")
        self.assertEqual(b"".join(r), b"helloworld")
        # Accessing .content still works.
        self.assertEqual(r.content, b"helloworld")

        # Accessing .content also works if the response was iterated first.
        r = HttpResponse(iter(["hello", "world"]))
        self.assertEqual(b"".join(r), b"helloworld")
        self.assertEqual(r.content, b"helloworld")

        # Additional content can be written to the response.
        r = HttpResponse(iter(["hello", "world"]))
        self.assertEqual(r.content, b"helloworld")
        r.write("!")
        self.assertEqual(r.content, b"helloworld!")

    def test_iterator_isnt_rewound(self):
        # Regression test for #13222
        r = HttpResponse("abc")
        i = iter(r)
        self.assertEqual(list(i), [b"abc"])
        self.assertEqual(list(i), [])

    def test_lazy_content(self):
        r = HttpResponse(lazystr("helloworld"))
        self.assertEqual(r.content, b"helloworld")

    def test_file_interface(self):
        r = HttpResponse()
        r.write(b"hello")
        self.assertEqual(r.tell(), 5)
        r.write("привет")
        self.assertEqual(r.tell(), 17)

        r = HttpResponse(["abc"])
        r.write("def")
        self.assertEqual(r.tell(), 6)
        self.assertEqual(r.content, b"abcdef")

        # with Content-Encoding header
        r = HttpResponse()
        r.headers["Content-Encoding"] = "winning"
        r.write(b"abc")
        r.write(b"def")
        self.assertEqual(r.content, b"abcdef")

    def test_stream_interface(self):
        r = HttpResponse("asdf")
        self.assertEqual(r.getvalue(), b"asdf")

        r = HttpResponse()
        self.assertIs(r.writable(), True)
        r.writelines(["foo\n", "bar\n", "baz\n"])
        self.assertEqual(r.content, b"foo\nbar\nbaz\n")

    def test_unsafe_redirect(self):
        bad_urls = [
            'data:text/html,<script>window.alert("xss")</script>',
            "mailto:test@example.com",
            "file:///etc/passwd",
        ]
        for url in bad_urls:
            with self.assertRaises(DisallowedRedirect):
                HttpResponseRedirect(url)
            with self.assertRaises(DisallowedRedirect):
                HttpResponsePermanentRedirect(url)

    def test_header_deletion(self):
        r = HttpResponse("hello")
        r.headers["X-Foo"] = "foo"
        del r.headers["X-Foo"]
        self.assertNotIn("X-Foo", r.headers)
        # del doesn't raise a KeyError on nonexistent headers.
        del r.headers["X-Foo"]

    def test_instantiate_with_headers(self):
        r = HttpResponse("hello", headers={"X-Foo": "foo"})
        self.assertEqual(r.headers["X-Foo"], "foo")
        self.assertEqual(r.headers["x-foo"], "foo")

    def test_content_type(self):
        r = HttpResponse("hello", content_type="application/json")
        self.assertEqual(r.headers["Content-Type"], "application/json")

    def test_content_type_headers(self):
        r = HttpResponse("hello", headers={"Content-Type": "application/json"})
        self.assertEqual(r.headers["Content-Type"], "application/json")

    def test_content_type_mutually_exclusive(self):
        msg = (
            "'headers' must not contain 'Content-Type' when the "
            "'content_type' parameter is provided."
        )
        with self.assertRaisesMessage(ValueError, msg):
            HttpResponse(
                "hello",
                content_type="application/json",
                headers={"Content-Type": "text/csv"},
            )


class HttpResponseSubclassesTests(SimpleTestCase):
    def test_redirect(self):
        response = HttpResponseRedirect("/redirected/")
        self.assertEqual(response.status_code, 302)
        # Standard HttpResponse init args can be used
        response = HttpResponseRedirect(
            "/redirected/",
            content="The resource has temporarily moved",
        )
        self.assertContains(
            response, "The resource has temporarily moved", status_code=302
        )
        self.assertEqual(response.url, response.headers["Location"])

    def test_redirect_lazy(self):
        """Make sure HttpResponseRedirect works with lazy strings."""
        r = HttpResponseRedirect(lazystr("/redirected/"))
        self.assertEqual(r.url, "/redirected/")

    def test_redirect_repr(self):
        response = HttpResponseRedirect("/redirected/")
        expected = (
            '<HttpResponseRedirect status_code=302, "text/html; charset=utf-8", '
            'url="/redirected/">'
        )
        self.assertEqual(repr(response), expected)

    def test_invalid_redirect_repr(self):
        """
        If HttpResponseRedirect raises DisallowedRedirect, its __repr__()
        should work (in the debug view, for example).
        """
        response = HttpResponseRedirect.__new__(HttpResponseRedirect)
        with self.assertRaisesMessage(
            DisallowedRedirect, "Unsafe redirect to URL with protocol 'ssh'"
        ):
            HttpResponseRedirect.__init__(response, "ssh://foo")
        expected = (
            '<HttpResponseRedirect status_code=302, "text/html; charset=utf-8", '
            'url="ssh://foo">'
        )
        self.assertEqual(repr(response), expected)

    def test_not_modified(self):
        response = HttpResponseNotModified()
        self.assertEqual(response.status_code, 304)
        # 304 responses should not have content/content-type
        with self.assertRaises(AttributeError):
            response.content = "Hello dear"
        self.assertNotIn("content-type", response)

    def test_not_modified_repr(self):
        response = HttpResponseNotModified()
        self.assertEqual(repr(response), "<HttpResponseNotModified status_code=304>")

    def test_not_allowed(self):
        response = HttpResponseNotAllowed(["GET"])
        self.assertEqual(response.status_code, 405)
        # Standard HttpResponse init args can be used
        response = HttpResponseNotAllowed(
            ["GET"], content="Only the GET method is allowed"
        )
        self.assertContains(response, "Only the GET method is allowed", status_code=405)

    def test_not_allowed_repr(self):
        response = HttpResponseNotAllowed(["GET", "OPTIONS"], content_type="text/plain")
        expected = (
            '<HttpResponseNotAllowed [GET, OPTIONS] status_code=405, "text/plain">'
        )
        self.assertEqual(repr(response), expected)

    def test_not_allowed_repr_no_content_type(self):
        response = HttpResponseNotAllowed(("GET", "POST"))
        del response.headers["Content-Type"]
        self.assertEqual(
            repr(response), "<HttpResponseNotAllowed [GET, POST] status_code=405>"
        )


class JsonResponseTests(SimpleTestCase):
    def test_json_response_non_ascii(self):
        data = {"key": "łóżko"}
        response = JsonResponse(data)
        self.assertEqual(json.loads(response.content.decode()), data)

    def test_json_response_raises_type_error_with_default_setting(self):
        with self.assertRaisesMessage(
            TypeError,
            "In order to allow non-dict objects to be serialized set the "
            "safe parameter to False",
        ):
            JsonResponse([1, 2, 3])

    def test_json_response_text(self):
        response = JsonResponse("foobar", safe=False)
        self.assertEqual(json.loads(response.content.decode()), "foobar")

    def test_json_response_list(self):
        response = JsonResponse(["foo", "bar"], safe=False)
        self.assertEqual(json.loads(response.content.decode()), ["foo", "bar"])

    def test_json_response_uuid(self):
        u = uuid.uuid4()
        response = JsonResponse(u, safe=False)
        self.assertEqual(json.loads(response.content.decode()), str(u))

    def test_json_response_custom_encoder(self):
        class CustomDjangoJSONEncoder(DjangoJSONEncoder):
            def encode(self, o):
                return json.dumps({"foo": "bar"})

        response = JsonResponse({}, encoder=CustomDjangoJSONEncoder)
        self.assertEqual(json.loads(response.content.decode()), {"foo": "bar"})

    def test_json_response_passing_arguments_to_json_dumps(self):
        response = JsonResponse({"foo": "bar"}, json_dumps_params={"indent": 2})
        self.assertEqual(response.content.decode(), '{\n  "foo": "bar"\n}')


class StreamingHttpResponseTests(SimpleTestCase):
    def test_streaming_response(self):
        r = StreamingHttpResponse(iter(["hello", "world"]))

        # iterating over the response itself yields bytestring chunks.
        chunks = list(r)
        self.assertEqual(chunks, [b"hello", b"world"])
        for chunk in chunks:
            self.assertIsInstance(chunk, bytes)

        # and the response can only be iterated once.
        self.assertEqual(list(r), [])

        # even when a sequence that can be iterated many times, like a list,
        # is given as content.
        r = StreamingHttpResponse(["abc", "def"])
        self.assertEqual(list(r), [b"abc", b"def"])
        self.assertEqual(list(r), [])

        # iterating over strings still yields bytestring chunks.
        r.streaming_content = iter(["hello", "café"])
        chunks = list(r)
        # '\xc3\xa9' == unichr(233).encode()
        self.assertEqual(chunks, [b"hello", b"caf\xc3\xa9"])
        for chunk in chunks:
            self.assertIsInstance(chunk, bytes)

        # streaming responses don't have a `content` attribute.
        self.assertFalse(hasattr(r, "content"))

        # and you can't accidentally assign to a `content` attribute.
        with self.assertRaises(AttributeError):
            r.content = "xyz"

        # but they do have a `streaming_content` attribute.
        self.assertTrue(hasattr(r, "streaming_content"))

        # that exists so we can check if a response is streaming, and wrap or
        # replace the content iterator.
        r.streaming_content = iter(["abc", "def"])
        r.streaming_content = (chunk.upper() for chunk in r.streaming_content)
        self.assertEqual(list(r), [b"ABC", b"DEF"])

        # coercing a streaming response to bytes doesn't return a complete HTTP
        # message like a regular response does. it only gives us the headers.
        r = StreamingHttpResponse(iter(["hello", "world"]))
        self.assertEqual(bytes(r), b"Content-Type: text/html; charset=utf-8")

        # and this won't consume its content.
        self.assertEqual(list(r), [b"hello", b"world"])

        # additional content cannot be written to the response.
        r = StreamingHttpResponse(iter(["hello", "world"]))
        with self.assertRaises(Exception):
            r.write("!")

        # and we can't tell the current position.
        with self.assertRaises(Exception):
            r.tell()

        r = StreamingHttpResponse(iter(["hello", "world"]))
        self.assertEqual(r.getvalue(), b"helloworld")

    def test_repr(self):
        r = StreamingHttpResponse(iter(["hello", "café"]))
        self.assertEqual(
            repr(r),
            '<StreamingHttpResponse status_code=200, "text/html; charset=utf-8">',
        )

    async def test_async_streaming_response(self):
        async def async_iter():
            yield b"hello"
            yield b"world"

        r = StreamingHttpResponse(async_iter())

        chunks = []
        async for chunk in r:
            chunks.append(chunk)
        self.assertEqual(chunks, [b"hello", b"world"])

    def test_async_streaming_response_warning(self):
        async def async_iter():
            yield b"hello"
            yield b"world"

        r = StreamingHttpResponse(async_iter())

        msg = (
            "StreamingHttpResponse must consume asynchronous iterators in order to "
            "serve them synchronously. Use a synchronous iterator instead."
        )
        with self.assertWarnsMessage(Warning, msg):
            self.assertEqual(list(r), [b"hello", b"world"])

    async def test_sync_streaming_response_warning(self):
        r = StreamingHttpResponse(iter(["hello", "world"]))

        msg = (
            "StreamingHttpResponse must consume synchronous iterators in order to "
            "serve them asynchronously. Use an asynchronous iterator instead."
        )
        with self.assertWarnsMessage(Warning, msg):
            self.assertEqual(b"hello", await r.__aiter__().__anext__())


class FileCloseTests(SimpleTestCase):
    def setUp(self):
        # Disable the request_finished signal during this test
        # to avoid interfering with the database connection.
        request_finished.disconnect(close_old_connections)

    def tearDown(self):
        request_finished.connect(close_old_connections)

    def test_response(self):
        filename = os.path.join(os.path.dirname(__file__), "abc.txt")

        # file isn't closed until we close the response.
        file1 = open(filename)
        r = HttpResponse(file1)
        self.assertTrue(file1.closed)
        r.close()

        # when multiple file are assigned as content, make sure they are all
        # closed with the response.
        file1 = open(filename)
        file2 = open(filename)
        r = HttpResponse(file1)
        r.content = file2
        self.assertTrue(file1.closed)
        self.assertTrue(file2.closed)

    def test_streaming_response(self):
        filename = os.path.join(os.path.dirname(__file__), "abc.txt")

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
        """Semicolons and commas are encoded."""
        c = SimpleCookie()
        c["test"] = "An,awkward;value"
        self.assertNotIn(";", c.output().rstrip(";"))  # IE compat
        self.assertNotIn(",", c.output().rstrip(";"))  # Safari compat

    def test_decode(self):
        """Semicolons and commas are decoded."""
        c = SimpleCookie()
        c["test"] = "An,awkward;value"
        c2 = SimpleCookie()
        c2.load(c.output()[12:])
        self.assertEqual(c["test"].value, c2["test"].value)
        c3 = parse_cookie(c.output()[12:])
        self.assertEqual(c["test"].value, c3["test"])

    def test_nonstandard_keys(self):
        """
        A single non-standard cookie name doesn't affect all cookies (#13007).
        """
        self.assertIn("good_cookie", parse_cookie("good_cookie=yes;bad:cookie=yes"))

    def test_repeated_nonstandard_keys(self):
        """
        A repeated non-standard name doesn't affect all cookies (#15852).
        """
        self.assertIn("good_cookie", parse_cookie("a:=b; a:=c; good_cookie=yes"))

    def test_python_cookies(self):
        """
        Test cases copied from Python's Lib/test/test_http_cookies.py
        """
        self.assertEqual(
            parse_cookie("chips=ahoy; vienna=finger"),
            {"chips": "ahoy", "vienna": "finger"},
        )
        # Here parse_cookie() differs from Python's cookie parsing in that it
        # treats all semicolons as delimiters, even within quotes.
        self.assertEqual(
            parse_cookie('keebler="E=mc2; L=\\"Loves\\"; fudge=\\012;"'),
            {"keebler": '"E=mc2', "L": '\\"Loves\\"', "fudge": "\\012", "": '"'},
        )
        # Illegal cookies that have an '=' char in an unquoted value.
        self.assertEqual(parse_cookie("keebler=E=mc2"), {"keebler": "E=mc2"})
        # Cookies with ':' character in their name.
        self.assertEqual(
            parse_cookie("key:term=value:term"), {"key:term": "value:term"}
        )
        # Cookies with '[' and ']'.
        self.assertEqual(
            parse_cookie("a=b; c=[; d=r; f=h"), {"a": "b", "c": "[", "d": "r", "f": "h"}
        )

    def test_cookie_edgecases(self):
        # Cookies that RFC 6265 allows.
        self.assertEqual(
            parse_cookie("a=b; Domain=example.com"), {"a": "b", "Domain": "example.com"}
        )
        # parse_cookie() has historically kept only the last cookie with the
        # same name.
        self.assertEqual(parse_cookie("a=b; h=i; a=c"), {"a": "c", "h": "i"})

    def test_invalid_cookies(self):
        """
        Cookie strings that go against RFC 6265 but browsers will send if set
        via document.cookie.
        """
        # Chunks without an equals sign appear as unnamed values per
        # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
        self.assertIn(
            "django_language", parse_cookie("abc=def; unnamed; django_language=en")
        )
        # Even a double quote may be an unnamed value.
        self.assertEqual(parse_cookie('a=b; "; c=d'), {"a": "b", "": '"', "c": "d"})
        # Spaces in names and values, and an equals sign in values.
        self.assertEqual(
            parse_cookie("a b c=d e = f; gh=i"), {"a b c": "d e = f", "gh": "i"}
        )
        # More characters the spec forbids.
        self.assertEqual(
            parse_cookie('a   b,c<>@:/[]?{}=d  "  =e,f g'),
            {"a   b,c<>@:/[]?{}": 'd  "  =e,f g'},
        )
        # Unicode characters. The spec only allows ASCII.
        self.assertEqual(
            parse_cookie("saint=André Bessette"), {"saint": "André Bessette"}
        )
        # Browsers don't send extra whitespace or semicolons in Cookie headers,
        # but parse_cookie() should parse whitespace the same way
        # document.cookie parses whitespace.
        self.assertEqual(
            parse_cookie("  =  b  ;  ;  =  ;   c  =  ;  "), {"": "b", "c": ""}
        )

    def test_samesite(self):
        c = SimpleCookie("name=value; samesite=lax; httponly")
        self.assertEqual(c["name"]["samesite"], "lax")
        self.assertIn("SameSite=lax", c.output())

    def test_httponly_after_load(self):
        c = SimpleCookie()
        c.load("name=val")
        c["name"]["httponly"] = True
        self.assertTrue(c["name"]["httponly"])

    def test_load_dict(self):
        c = SimpleCookie()
        c.load({"name": "val"})
        self.assertEqual(c["name"].value, "val")

    def test_pickle(self):
        rawdata = 'Customer="WILE_E_COYOTE"; Path=/acme; Version=1'
        expected_output = "Set-Cookie: %s" % rawdata

        C = SimpleCookie()
        C.load(rawdata)
        self.assertEqual(C.output(), expected_output)

        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            C1 = pickle.loads(pickle.dumps(C, protocol=proto))
            self.assertEqual(C1.output(), expected_output)


class HttpResponseHeadersTestCase(SimpleTestCase):
    """Headers by treating HttpResponse like a dictionary."""

    def test_headers(self):
        response = HttpResponse()
        response["X-Foo"] = "bar"
        self.assertEqual(response["X-Foo"], "bar")
        self.assertEqual(response.headers["X-Foo"], "bar")
        self.assertIn("X-Foo", response)
        self.assertIs(response.has_header("X-Foo"), True)
        del response["X-Foo"]
        self.assertNotIn("X-Foo", response)
        self.assertNotIn("X-Foo", response.headers)
        # del doesn't raise a KeyError on nonexistent headers.
        del response["X-Foo"]

    def test_headers_as_iterable_of_tuple_pairs(self):
        response = HttpResponse(headers=(("X-Foo", "bar"),))
        self.assertEqual(response["X-Foo"], "bar")

    def test_headers_bytestring(self):
        response = HttpResponse()
        response["X-Foo"] = b"bar"
        self.assertEqual(response["X-Foo"], "bar")
        self.assertEqual(response.headers["X-Foo"], "bar")

    def test_newlines_in_headers(self):
        response = HttpResponse()
        with self.assertRaises(BadHeaderError):
            response["test\rstr"] = "test"
        with self.assertRaises(BadHeaderError):
            response["test\nstr"] = "test"

import unittest

from django.core.exceptions import SuspiciousMultipartForm
from django.http import multipartparser


class LazyStreamTests(unittest.TestCase):
    def test_lazy_stream_iteration_scenario(self):
        stream = multipartparser.LazyStream(iter([b'1', b'2', b'3']))
        item = next(stream)
        self.assertEqual(item, b'1')
        item = next(stream)
        self.assertEqual(item, b'2')
        item = next(stream)
        self.assertEqual(item, b'3')
        with self.assertRaises(StopIteration):
            next(stream)

    def test_lazy_stream_unget_scenario(self):
        stream = multipartparser.LazyStream(iter([b'1', b'2', b'3']))
        item = next(stream)
        self.assertEqual(item, b'1')

        stream.unget(b'4')

        item = next(stream)
        self.assertEqual(item, b'4')
        item = next(stream)
        self.assertEqual(item, b'2')
        item = next(stream)
        self.assertEqual(item, b'3')
        with self.assertRaises(StopIteration):
            next(stream)

    def test_lazy_stream_full_read_operation_with_ungetting_before(self):
        stream = multipartparser.LazyStream(iter([b'4', b'5', b'6']))
        stream.unget(b'123')
        self.assertEqual(stream.read(), b'123456')

    def test_lazy_stream_partial_read_operation_with_ungetting_before(self):
        stream = multipartparser.LazyStream(iter([b'4', b'5', b'6']))
        stream.unget(b'123')
        self.assertEqual(stream.read(size=2), b'12')
        self.assertEqual(stream.read(size=2), b'34')
        self.assertEqual(stream.read(size=2), b'56')

    def test_lazy_stream_read_until_stop_iteration(self):

        stream = multipartparser.LazyStream(iter([b'1', b'2', b'3']))
        self.assertEqual(stream.read(size=1), b'1')
        self.assertEqual(stream.read(size=1), b'2')
        self.assertEqual(stream.read(size=1), b'3')
        self.assertEqual(stream.read(size=1), b'')
        self.assertEqual(stream.read(size=1), b'')
        self.assertEqual(stream.read(size=1), b'')
        self.assertEqual(stream.read(size=1), b'')
        self.assertEqual(stream.read(size=1), b'')
        self.assertEqual(stream.read(size=1), b'')

    def test_lazy_stream_close_stream_and_try_to_read_should_fail(self):
        stream = multipartparser.LazyStream(iter([b'4', b'5', b'6']))
        stream.close()
        with self.assertRaises(Exception):
            # TypeError: 'list' object is not an iterator
            stream.read()

    def test_lazy_stream_unget_should_change_tell_result(self):
        stream = multipartparser.LazyStream(iter([b'4', b'5', b'6']))
        next(stream)
        self.assertEqual(stream.tell(), 1)
        next(stream)
        self.assertEqual(stream.tell(), 2)
        stream.unget(b'1')
        self.assertEqual(stream.tell(), 1)
        next(stream)
        self.assertEqual(stream.tell(), 2)
        stream.unget(b'1')
        self.assertEqual(stream.tell(), 1)
        stream.unget(b'2')
        self.assertEqual(stream.tell(), 0)
        stream.unget(b'3')
        self.assertEqual(stream.tell(), -1)
        stream.unget(b'4')
        self.assertEqual(stream.tell(), -2)

    def test_lazy_stream_with_a_maliciously_malformed_mime_request(self):
        stream = multipartparser.LazyStream(iter([]))
        with self.assertRaises(SuspiciousMultipartForm):
            while True:
                stream.unget(b"Hey :D")

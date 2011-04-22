from django.utils import http
from django.utils import unittest
from django.utils.datastructures import MultiValueDict

class TestUtilsHttp(unittest.TestCase):

    def test_same_origin_true(self):
        # Identical
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com/'))
        # One with trailing slash - see #15617
        self.assertTrue(http.same_origin('http://foo.com', 'http://foo.com/'))
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com'))
        # With port
        self.assertTrue(http.same_origin('https://foo.com:8000', 'https://foo.com:8000/'))

    def test_same_origin_false(self):
        # Different scheme
        self.assertFalse(http.same_origin('http://foo.com', 'https://foo.com'))
        # Different host
        self.assertFalse(http.same_origin('http://foo.com', 'http://goo.com'))
        # Different host again
        self.assertFalse(http.same_origin('http://foo.com', 'http://foo.com.evil.com'))
        # Different port
        self.assertFalse(http.same_origin('http://foo.com:8000', 'http://foo.com:8001'))

    def test_urlencode(self):
        # 2-tuples (the norm)
        result = http.urlencode((('a', 1), ('b', 2), ('c', 3)))
        self.assertEqual(result, 'a=1&b=2&c=3')
        # A dictionary
        result = http.urlencode({ 'a': 1, 'b': 2, 'c': 3})
        acceptable_results = [
            # Need to allow all of these as dictionaries have to be treated as
            # unordered
            'a=1&b=2&c=3',
            'a=1&c=3&b=2',
            'b=2&a=1&c=3',
            'b=2&c=3&a=1',
            'c=3&a=1&b=2',
            'c=3&b=2&a=1'
        ]
        self.assertTrue(result in acceptable_results)
        # A MultiValueDict
        result = http.urlencode(MultiValueDict({
            'name': ['Adrian', 'Simon'],
            'position': ['Developer']
        }), doseq=True)
        acceptable_results = [
            # MultiValueDicts are similarly unordered
            'name=Adrian&name=Simon&position=Developer',
            'position=Developer&name=Adrian&name=Simon'
        ]
        self.assertTrue(result in acceptable_results)

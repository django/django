"Unit tests for reverse URL lookup"

from django.core.urlresolvers import reverse_helper, NoReverseMatch
import re, unittest

test_data = (
    ('^places/(\d+)/$', 'places/3/', [3], {}),
    ('^places/(\d+)/$', 'places/3/', ['3'], {}),
    ('^places/(\d+)/$', NoReverseMatch, ['a'], {}),
    ('^places/(\d+)/$', NoReverseMatch, [], {}),
    ('^places/(?P<id>\d+)/$', 'places/3/', [], {'id': 3}),
    ('^people/(?P<name>\w+)/$', 'people/adrian/', ['adrian'], {}),
    ('^people/(?P<name>\w+)/$', 'people/adrian/', [], {'name': 'adrian'}),
    ('^people/(?P<name>\w+)/$', NoReverseMatch, ['name with spaces'], {}),
    ('^people/(?P<name>\w+)/$', NoReverseMatch, [], {'name': 'name with spaces'}),
    ('^people/(?P<name>\w+)/$', NoReverseMatch, [], {}),
    ('^hardcoded/$', 'hardcoded/', [], {}),
    ('^hardcoded/$', 'hardcoded/', ['any arg'], {}),
    ('^hardcoded/$', 'hardcoded/', [], {'kwarg': 'foo'}),
    ('^people/(?P<state>\w\w)/(?P<name>\w+)/$', 'people/il/adrian/', [], {'state': 'il', 'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(?P<name>\d)/$', NoReverseMatch, [], {'state': 'il', 'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(?P<name>\w+)/$', NoReverseMatch, [], {'state': 'il'}),
    ('^people/(?P<state>\w\w)/(?P<name>\w+)/$', NoReverseMatch, [], {'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(\w+)/$', NoReverseMatch, ['il'], {'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(\w+)/$', 'people/il/adrian/', ['adrian'], {'state': 'il'}),
)

class URLPatternReverse(unittest.TestCase):
    def test_urlpattern_reverse(self):
        for regex, expected, args, kwargs in test_data:
            try:
                got = reverse_helper(re.compile(regex), *args, **kwargs)
            except NoReverseMatch, e:
                self.assertEqual(expected, NoReverseMatch)
            else:
                self.assertEquals(got, expected)

if __name__ == "__main__":
    run_tests(1)

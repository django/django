"""
Unit tests for reverse URL lookups.
"""

import re
import unittest

from django.core.urlresolvers import reverse_helper, NoReverseMatch

test_data = (
    ('^places/(\d+)/$', 'places/3/', [3], {}),
    ('^places/(\d+)/$', 'places/3/', ['3'], {}),
    ('^places/(\d+)/$', NoReverseMatch, ['a'], {}),
    ('^places/(\d+)/$', NoReverseMatch, [], {}),
    ('^places?/$', '/', [], {}),
    ('^places+/$', 'places/', [], {}),
    ('^places*/$', '/', [], {}),
    (r'^places/(\d+|[a-z_]+)/', 'places/4/', [4], {}),
    (r'^places/(\d+|[a-z_]+)/', 'places/harlem/', ['harlem'], {}),
    (r'^places/(\d+|[a-z_]+)/', NoReverseMatch, ['harlem64'], {}),
    ('^places/(?P<id>\d+)/$', 'places/3/', [], {'id': 3}),
    ('^people/(?P<name>\w+)/$', NoReverseMatch, [], {}),
    ('^people/(?P<name>\w+)/$', 'people/adrian/', ['adrian'], {}),
    ('^people/(?P<name>\w+)/$', 'people/adrian/', [], {'name': 'adrian'}),
    ('^people/(?P<name>\w+)/$', NoReverseMatch, ['name with spaces'], {}),
    ('^people/(?P<name>\w+)/$', NoReverseMatch, [], {'name': 'name with spaces'}),
    ('^people/(?:name/)', 'people/name/', [], {}),
    ('^people/(?:name/)?', 'people/', [], {}),
    ('^people/(?:name/(\w+)/)?', 'people/name/fred/', ['fred'], {}),
    ('^hardcoded/$', 'hardcoded/', [], {}),
    ('^hardcoded/$', 'hardcoded/', ['any arg'], {}),
    ('^hardcoded/$', 'hardcoded/', [], {'kwarg': 'foo'}),
    ('^hardcoded/doc\\.pdf$', 'hardcoded/doc.pdf', [], {}),
    ('^people/(?P<state>\w\w)/(?P<name>\w+)/$', 'people/il/adrian/', [], {'state': 'il', 'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(?P<name>\d)/$', NoReverseMatch, [], {'state': 'il', 'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(?P<name>\w+)/$', NoReverseMatch, [], {'state': 'il'}),
    ('^people/(?P<state>\w\w)/(?P<name>\w+)/$', NoReverseMatch, [], {'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(\w+)/$', NoReverseMatch, ['il'], {'name': 'adrian'}),
    ('^people/(?P<state>\w\w)/(\w+)/$', 'people/il/adrian/', ['adrian'], {'state': 'il'}),
    (r'^people/((?P<state>\w\w)/test)?/(\w+)/$', 'people/il/test/adrian/', ['adrian'], {'state': 'il'}),
    (r'^people/((?P<state>\w\w)/test)?/(\w+)/$', NoReverseMatch, ['adrian'], {}),
    ('^character_set/[abcdef0-9]/$', 'character_set/a/', [], {}),
    ('^character_set/[\w]/$', 'character_set/a/', [], {}),
    (r'^price/\$(\d+)/$', 'price/$10/', ['10'], {}),
    (r'^price/[$](\d+)/$', 'price/$10/', ['10'], {}),
    (r'^price/[\$](\d+)/$', 'price/$10/', ['10'], {}),
    (r'^product/(?P<product>\w+)\+\(\$(?P<price>\d+(\.\d+)?)\)/$', 'product/chocolate+($2.00)/', ['2.00'], {'product': 'chocolate'}),
    (r'^headlines/(?P<year>\d+)\.(?P<month>\d+)\.(?P<day>\d+)/$', 'headlines/2007.5.21/', [], dict(year=2007, month=5, day=21)),
    (r'^windows_path/(?P<drive_name>[A-Z]):\\(?P<path>.+)/$', r'windows_path/C:\Documents and Settings\spam/', [], dict(drive_name='C', path=r'Documents and Settings\spam')),
    (r'^special_chars/(.+)/$', r'special_chars/+\$*/', [r'+\$*'], {}),
    (r'^special_chars/(.+)/$', NoReverseMatch, [''], {}),
    (r'^(?P<name>.+)/\d+/$', NoReverseMatch, [], {'name': 'john'}),
    (r'^repeats/a{1,2}/$', 'repeats/a/', [], {}),
    (r'^repeats/a{2,4}/$', 'repeats/aa/', [], {}),
    (r'^people/(?:(?:wilma|fred)/)$', '/people/wilma', [], {}),
)

class URLPatternReverse(unittest.TestCase):
    def test_urlpattern_reverse(self):
        for regex, expected, args, kwargs in test_data:
            try:
                got = reverse_helper(regex, *args, **kwargs)
            except NoReverseMatch, e:
                self.assertEqual(expected, NoReverseMatch)
            else:
                self.assertEquals(got, expected)


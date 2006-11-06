"Unit tests for reverse URL lookup"

from django.core.urlresolvers import reverse_helper, NoReverseMatch
import re

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

def run_tests(verbosity=0):
    for regex, expected, args, kwargs in test_data:
        passed = True
        try:
            got = reverse_helper(re.compile(regex), *args, **kwargs)
        except NoReverseMatch, e:
            if expected != NoReverseMatch:
                passed, got = False, str(e)
        else:
            if got != expected:
                passed, got = False, got
        if passed and verbosity:
            print "Passed: %s" % regex
        elif not passed:
            print "REVERSE LOOKUP FAILED: %s" % regex
            print "   Got: %s" % got
            print "   Expected: %r" % expected

if __name__ == "__main__":
    run_tests(1)

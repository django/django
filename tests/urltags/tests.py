from django.conf.urls import include, url
from django.core.urlresolvers import resolve
from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings

import json


def test_view(request):
    """
    Returns the tags attached to the request in the response, so they can be veried in tests
    """
    return HttpResponse(json.dumps(list(request.resolver_match.tags)))

sub_sub_patterns = [
    url(r'^a/$', test_view, name='s-s-p1'),
    url(r'^b/$', test_view, name='s-s-p2', tags=['s-s-t1', 's-s-t2']),
    url(r'^c/$', test_view, name='s-s-p3', tags=['s-s-t1', 't4']),
]

sub_patterns = [
    url(r'^a/$', test_view, name='s-p1'),
    url(r'^b/$', test_view, name='s-p2', tags=['s-t1']),
    url(r'^c/', include(sub_sub_patterns), tags=['s-t2']),

]

urlpatterns = [
    url(r'^$', test_view, name='p1'),
    url(r'^a/$', test_view, name='p2', tags=['t1']),
    url(r'^b/$', test_view, name='p2', tags=['t2', 't3']),
    url(r'^c/', include(sub_patterns), tags=['t4']),
]


@override_settings(ROOT_URLCONF='urltags.tests')
class URLTagsTests(SimpleTestCase):
    def test_no_tags(self):
        """
        Verifies url pattern with no tags specified
        """
        match = resolve('/')
        self.assertEqual(len(match.tags), 0)

    def test_single_tag(self):
        """
        Verifies url pattern with a single tag
        """
        match = resolve('/a/')
        self.assertEqual(len(match.tags), 1)
        self.assertTrue('t1' in match.tags)

    def test_multiple_tags(self):
        """
        Verifies url pattern with a multiple tags
        """
        match = resolve('/b/')
        self.assertEqual(len(match.tags), 2)
        self.assertTrue('t2' in match.tags)
        self.assertTrue('t3' in match.tags)

    def test_include1(self):
        """
        Verifies that a single tag is correctly propagated to included pattern
        """
        match = resolve('/c/a/')
        self.assertEqual(len(match.tags), 1)
        self.assertTrue('t4' in match.tags)

    def test_include2(self):
        """
        Verifies that tags are correctly combined with included patterns
        """
        match = resolve('/c/b/')
        self.assertEqual(len(match.tags), 2)
        self.assertTrue('t4' in match.tags)
        self.assertTrue('s-t1' in match.tags)

    def test_include3(self):
        """
        Verifies that tags are correctly combined with multi-level included patterns
        """
        match = resolve('/c/c/a/')
        self.assertEqual(len(match.tags), 2)
        self.assertTrue('t4' in match.tags)
        self.assertTrue('s-t2' in match.tags)

    def test_include4(self):
        """
        Verifies that multiple tags are correctly combined with multi-level included patterns
        """
        match = resolve('/c/c/b/')
        self.assertEqual(len(match.tags), 4)
        self.assertTrue('t4' in match.tags)
        self.assertTrue('s-t2' in match.tags)
        self.assertTrue('s-s-t1' in match.tags)
        self.assertTrue('s-s-t2' in match.tags)

    def test_include5(self):
        """
        Verifies that tags repeated in included patterns are correctly handled
        """
        match = resolve('/c/c/c/')
        self.assertEqual(len(match.tags), 3)
        self.assertTrue('t4' in match.tags)
        self.assertTrue('s-t2' in match.tags)
        self.assertTrue('s-s-t1' in match.tags)

    def test_request(self):
        """
        Verifies that tags can be accessed from within the request object
        """
        response = self.client.get('/c/c/c/')
        tags = set(json.loads(response.content))
        self.assertEqual(len(tags), 3)
        self.assertTrue('t4' in tags)
        self.assertTrue('s-t2' in tags)
        self.assertTrue('s-s-t1' in tags)

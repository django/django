# -*- coding: utf-8 -*-

from xml.dom import minidom
from django.test import TestCase
from django.test.client import Client
from models import Entry
try:
    set
except NameError:
    from sets import Set as set

class SyndicationFeedTest(TestCase):
    fixtures = ['feeddata.json']

    def assertChildNodes(self, elem, expected):
        actual = set([n.nodeName for n in elem.childNodes])
        expected = set(expected)
        self.assertEqual(actual, expected)

    def test_rss_feed(self):
        response = self.client.get('/syndication/feeds/rss/')
        doc = minidom.parseString(response.content)
        self.assertEqual(len(doc.getElementsByTagName('channel')), 1)

        chan = doc.getElementsByTagName('channel')[0]
        self.assertChildNodes(chan, ['title', 'link', 'description', 'language', 'lastBuildDate', 'item'])
    
        items = chan.getElementsByTagName('item')
        self.assertEqual(len(items), Entry.objects.count())
        for item in items:
            self.assertChildNodes(item, ['title', 'link', 'description', 'guid'])
    
    def test_atom_feed(self):
        response = self.client.get('/syndication/feeds/atom/')
        doc = minidom.parseString(response.content)
        
        feed = doc.firstChild
        self.assertEqual(feed.nodeName, 'feed')
        self.assertChildNodes(feed, ['title', 'link', 'id', 'updated', 'entry'])        
        
        entries = feed.getElementsByTagName('entry')
        self.assertEqual(len(entries), Entry.objects.count())
        for entry in entries:
            self.assertChildNodes(entry, ['title', 'link', 'id', 'summary'])
            summary = entry.getElementsByTagName('summary')[0]
            self.assertEqual(summary.getAttribute('type'), 'html')
    
    def test_custom_feed_generator(self):
        response = self.client.get('/syndication/feeds/custom/')
        doc = minidom.parseString(response.content)
        
        feed = doc.firstChild
        self.assertEqual(feed.nodeName, 'feed')
        self.assertEqual(feed.getAttribute('django'), 'rocks')
        self.assertChildNodes(feed, ['title', 'link', 'id', 'updated', 'entry', 'spam'])        
        
        entries = feed.getElementsByTagName('entry')
        self.assertEqual(len(entries), Entry.objects.count())
        for entry in entries:
            self.assertEqual(entry.getAttribute('bacon'), 'yum')
            self.assertChildNodes(entry, ['title', 'link', 'id', 'summary', 'ministry'])
            summary = entry.getElementsByTagName('summary')[0]
            self.assertEqual(summary.getAttribute('type'), 'html')
        
    def test_complex_base_url(self):
        """
        Tests that that the base url for a complex feed doesn't raise a 500
        exception.
        """
        response = self.client.get('/syndication/feeds/complex/')
        self.assertEquals(response.status_code, 404)



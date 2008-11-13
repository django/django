# coding: utf-8

from django.test import TestCase
from django.conf import settings

# local test models
from models import Episode, Media

class GenericAdminViewTest(TestCase):
    fixtures = ['users.xml', 'model-data.xml']

    def setUp(self):
        # set TEMPLATE_DEBUG to True to ensure {% include %} will raise
        # exceptions since that is how inlines are rendered and #9498 will
        # bubble up if it is an issue.
        self.original_template_debug = settings.TEMPLATE_DEBUG
        settings.TEMPLATE_DEBUG = True
        self.client.login(username='super', password='secret')
    
    def tearDown(self):
        self.client.logout()
        settings.TEMPLATE_DEBUG = self.original_template_debug
    
    def testBasicAddGet(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/add/')
        self.failUnlessEqual(response.status_code, 200)
    
    def testBasicEditGet(self):
        """
        A smoke test to ensure GET on the change_view works.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/1/')
        self.failUnlessEqual(response.status_code, 200)
    
    def testBasicAddPost(self):
        """
        A smoke test to ensure POST on add_view works.
        """
        post_data = {
            "name": u"This Week in Django",
            # inline data
            "generic_inline_admin-media-content_type-object_id-TOTAL_FORMS": u"1",
            "generic_inline_admin-media-content_type-object_id-INITIAL_FORMS": u"0",
        }
        response = self.client.post('/generic_inline_admin/admin/generic_inline_admin/episode/add/', post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere
    
    def testBasicEditPost(self):
        """
        A smoke test to ensure POST on edit_view works.
        """
        post_data = {
            "name": u"This Week in Django",
            # inline data
            "generic_inline_admin-media-content_type-object_id-TOTAL_FORMS": u"2",
            "generic_inline_admin-media-content_type-object_id-INITIAL_FORMS": u"1",
            "generic_inline_admin-media-content_type-object_id-0-id": u"1",
            "generic_inline_admin-media-content_type-object_id-0-url": u"http://example.com/podcast.mp3",
            "generic_inline_admin-media-content_type-object_id-1-id": u"",
            "generic_inline_admin-media-content_type-object_id-1-url": u"",
        }
        response = self.client.post('/generic_inline_admin/admin/generic_inline_admin/episode/1/', post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere

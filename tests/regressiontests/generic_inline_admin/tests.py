# coding: utf-8

from django.test import TestCase
from django.conf import settings
from django.contrib.contenttypes.generic import generic_inlineformset_factory

# local test models
from models import Episode, Media

class GenericAdminViewTest(TestCase):
    fixtures = ['users.xml']

    def setUp(self):
        # set TEMPLATE_DEBUG to True to ensure {% include %} will raise
        # exceptions since that is how inlines are rendered and #9498 will
        # bubble up if it is an issue.
        self.original_template_debug = settings.TEMPLATE_DEBUG
        settings.TEMPLATE_DEBUG = True
        self.client.login(username='super', password='secret')
        
        # Can't load content via a fixture (since the GenericForeignKey
        # relies on content type IDs, which will vary depending on what
        # other tests have been run), thus we do it here.
        e = Episode.objects.create(name='This Week in Django')
        self.episode_pk = e.pk
        m = Media(content_object=e, url='http://example.com/podcast.mp3')
        m.save()
        self.media_pk = m.pk
    
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
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/%d/' % self.episode_pk)
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
            "generic_inline_admin-media-content_type-object_id-0-id": u"%d" % self.media_pk,
            "generic_inline_admin-media-content_type-object_id-0-url": u"http://example.com/podcast.mp3",
            "generic_inline_admin-media-content_type-object_id-1-id": u"",
            "generic_inline_admin-media-content_type-object_id-1-url": u"",
        }
        url = '/generic_inline_admin/admin/generic_inline_admin/episode/%d/' % self.episode_pk
        response = self.client.post(url, post_data)
        self.failUnlessEqual(response.status_code, 302) # redirect somewhere
    
    def testGenericInlineFormsetFactory(self):
        # Regression test for #10522.
        inline_formset = generic_inlineformset_factory(Media,
            exclude=('url',))

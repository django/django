# coding: utf-8

from django.test import TestCase
from django.conf import settings
from django.contrib.contenttypes.generic import generic_inlineformset_factory

# local test models
from models import Episode, EpisodeExtra, EpisodeMaxNum, EpisodeExclude, Media

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

class GenericInlineAdminParametersTest(TestCase):
    fixtures = ['users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')
        
        # Can't load content via a fixture (since the GenericForeignKey
        # relies on content type IDs, which will vary depending on what
        # other tests have been run), thus we do it here.
        test_classes = [
            Episode,
            EpisodeExtra,
            EpisodeMaxNum,
            EpisodeExclude,
        ]
        for klass in test_classes:
            e = klass.objects.create(name='This Week in Django')
            m = Media(content_object=e, url='http://example.com/podcast.mp3')
            m.save()
    
    def tearDown(self):
        self.client.logout()

    def testNoParam(self):
        """
        With one initial form, extra (default) at 3, there should be 4 forms.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/1/')
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 4)
        self.assertEqual(formset.initial_form_count(), 1)

    def testExtraParam(self):
        """
        With extra=0, there should be one form.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episodeextra/2/')
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 1)
        self.assertEqual(formset.initial_form_count(), 1)

    def testMaxNumParam(self):
        """
        With extra=5 and max_num=2, there should be only 2 forms.
        """
        inline_form_data = '<input type="hidden" name="generic_inline_admin-media-content_type-object_id-TOTAL_FORMS" value="2" id="id_generic_inline_admin-media-content_type-object_id-TOTAL_FORMS" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-INITIAL_FORMS" value="1" id="id_generic_inline_admin-media-content_type-object_id-INITIAL_FORMS" />'
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episodemaxnum/3/')
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 2)
        self.assertEqual(formset.initial_form_count(), 1)

    def testExcludeParam(self):
        """
        Generic inline formsets should respect include.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episodeexclude/4/')
        formset = response.context['inline_admin_formsets'][0].formset
        self.failIf('url' in formset.forms[0], 'The formset has excluded "url" field.')
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.contenttypes.generic import (
    generic_inlineformset_factory, GenericTabularInline)
from django.forms.formsets import DEFAULT_MAX_NUM
from django.forms.models import ModelForm
from django.test import TestCase
from django.test.utils import override_settings

# local test models
from .admin import MediaInline, MediaPermanentInline
from .models import (Episode, EpisodeExtra, EpisodeMaxNum, Media,
    EpisodePermanent, Category)


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class GenericAdminViewTest(TestCase):
    urls = "regressiontests.generic_inline_admin.urls"
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
        self.mp3_media_pk = m.pk

        m = Media(content_object=e, url='http://example.com/logo.png')
        m.save()
        self.png_media_pk = m.pk

    def tearDown(self):
        self.client.logout()
        settings.TEMPLATE_DEBUG = self.original_template_debug

    def testBasicAddGet(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/add/')
        self.assertEqual(response.status_code, 200)

    def testBasicEditGet(self):
        """
        A smoke test to ensure GET on the change_view works.
        """
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/%d/' % self.episode_pk)
        self.assertEqual(response.status_code, 200)

    def testBasicAddPost(self):
        """
        A smoke test to ensure POST on add_view works.
        """
        post_data = {
            "name": "This Week in Django",
            # inline data
            "generic_inline_admin-media-content_type-object_id-TOTAL_FORMS": "1",
            "generic_inline_admin-media-content_type-object_id-INITIAL_FORMS": "0",
            "generic_inline_admin-media-content_type-object_id-MAX_NUM_FORMS": "0",
        }
        response = self.client.post('/generic_inline_admin/admin/generic_inline_admin/episode/add/', post_data)
        self.assertEqual(response.status_code, 302) # redirect somewhere

    def testBasicEditPost(self):
        """
        A smoke test to ensure POST on edit_view works.
        """
        post_data = {
            "name": "This Week in Django",
            # inline data
            "generic_inline_admin-media-content_type-object_id-TOTAL_FORMS": "3",
            "generic_inline_admin-media-content_type-object_id-INITIAL_FORMS": "2",
            "generic_inline_admin-media-content_type-object_id-MAX_NUM_FORMS": "0",
            "generic_inline_admin-media-content_type-object_id-0-id": "%d" % self.mp3_media_pk,
            "generic_inline_admin-media-content_type-object_id-0-url": "http://example.com/podcast.mp3",
            "generic_inline_admin-media-content_type-object_id-1-id": "%d" % self.png_media_pk,
            "generic_inline_admin-media-content_type-object_id-1-url": "http://example.com/logo.png",
            "generic_inline_admin-media-content_type-object_id-2-id": "",
            "generic_inline_admin-media-content_type-object_id-2-url": "",
        }
        url = '/generic_inline_admin/admin/generic_inline_admin/episode/%d/' % self.episode_pk
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302) # redirect somewhere

    def testGenericInlineFormset(self):
        EpisodeMediaFormSet = generic_inlineformset_factory(Media, can_delete=False, exclude=['description', 'keywords'], extra=3)
        e = Episode.objects.get(name='This Week in Django')

        # Works with no queryset
        formset = EpisodeMediaFormSet(instance=e)
        self.assertEqual(len(formset.forms), 5)
        self.assertHTMLEqual(formset.forms[0].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-0-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-0-url" type="text" name="generic_inline_admin-media-content_type-object_id-0-url" value="http://example.com/podcast.mp3" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-0-id" value="%s" id="id_generic_inline_admin-media-content_type-object_id-0-id" /></p>' % self.mp3_media_pk)
        self.assertHTMLEqual(formset.forms[1].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-1-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-1-url" type="text" name="generic_inline_admin-media-content_type-object_id-1-url" value="http://example.com/logo.png" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-1-id" value="%s" id="id_generic_inline_admin-media-content_type-object_id-1-id" /></p>' % self.png_media_pk)
        self.assertHTMLEqual(formset.forms[2].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-2-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-2-url" type="text" name="generic_inline_admin-media-content_type-object_id-2-url" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-2-id" id="id_generic_inline_admin-media-content_type-object_id-2-id" /></p>')

        # A queryset can be used to alter display ordering
        formset = EpisodeMediaFormSet(instance=e, queryset=Media.objects.order_by('url'))
        self.assertEqual(len(formset.forms), 5)
        self.assertHTMLEqual(formset.forms[0].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-0-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-0-url" type="text" name="generic_inline_admin-media-content_type-object_id-0-url" value="http://example.com/logo.png" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-0-id" value="%s" id="id_generic_inline_admin-media-content_type-object_id-0-id" /></p>' % self.png_media_pk)
        self.assertHTMLEqual(formset.forms[1].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-1-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-1-url" type="text" name="generic_inline_admin-media-content_type-object_id-1-url" value="http://example.com/podcast.mp3" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-1-id" value="%s" id="id_generic_inline_admin-media-content_type-object_id-1-id" /></p>' % self.mp3_media_pk)
        self.assertHTMLEqual(formset.forms[2].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-2-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-2-url" type="text" name="generic_inline_admin-media-content_type-object_id-2-url" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-2-id" id="id_generic_inline_admin-media-content_type-object_id-2-id" /></p>')

        # Works with a queryset that omits items
        formset = EpisodeMediaFormSet(instance=e, queryset=Media.objects.filter(url__endswith=".png"))
        self.assertEqual(len(formset.forms), 4)
        self.assertHTMLEqual(formset.forms[0].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-0-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-0-url" type="text" name="generic_inline_admin-media-content_type-object_id-0-url" value="http://example.com/logo.png" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-0-id" value="%s" id="id_generic_inline_admin-media-content_type-object_id-0-id" /></p>' % self.png_media_pk)
        self.assertHTMLEqual(formset.forms[1].as_p(), '<p><label for="id_generic_inline_admin-media-content_type-object_id-1-url">Url:</label> <input id="id_generic_inline_admin-media-content_type-object_id-1-url" type="text" name="generic_inline_admin-media-content_type-object_id-1-url" maxlength="200" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-1-id" id="id_generic_inline_admin-media-content_type-object_id-1-id" /></p>')

    def testGenericInlineFormsetFactory(self):
        # Regression test for #10522.
        inline_formset = generic_inlineformset_factory(Media,
            exclude=('url',))

        # Regression test for #12340.
        e = Episode.objects.get(name='This Week in Django')
        formset = inline_formset(instance=e)
        self.assertTrue(formset.get_queryset().ordered)

@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class GenericInlineAdminParametersTest(TestCase):
    urls = "regressiontests.generic_inline_admin.urls"
    fixtures = ['users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def _create_object(self, model):
        """
        Create a model with an attached Media object via GFK. We can't
        load content via a fixture (since the GenericForeignKey relies on
        content type IDs, which will vary depending on what other tests
        have been run), thus we do it here.
        """
        e = model.objects.create(name='This Week in Django')
        Media.objects.create(content_object=e, url='http://example.com/podcast.mp3')
        return e

    def testNoParam(self):
        """
        With one initial form, extra (default) at 3, there should be 4 forms.
        """
        e = self._create_object(Episode)
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episode/%s/' % e.pk)
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 4)
        self.assertEqual(formset.initial_form_count(), 1)

    def testExtraParam(self):
        """
        With extra=0, there should be one form.
        """
        e = self._create_object(EpisodeExtra)
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episodeextra/%s/' % e.pk)
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 1)
        self.assertEqual(formset.initial_form_count(), 1)

    def testMaxNumParam(self):
        """
        With extra=5 and max_num=2, there should be only 2 forms.
        """
        e = self._create_object(EpisodeMaxNum)
        inline_form_data = '<input type="hidden" name="generic_inline_admin-media-content_type-object_id-TOTAL_FORMS" value="2" id="id_generic_inline_admin-media-content_type-object_id-TOTAL_FORMS" /><input type="hidden" name="generic_inline_admin-media-content_type-object_id-INITIAL_FORMS" value="1" id="id_generic_inline_admin-media-content_type-object_id-INITIAL_FORMS" />'
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/episodemaxnum/%s/' % e.pk)
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 2)
        self.assertEqual(formset.initial_form_count(), 1)


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class GenericInlineAdminWithUniqueTogetherTest(TestCase):
    urls = "regressiontests.generic_inline_admin.urls"
    fixtures = ['users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testAdd(self):
        category_id = Category.objects.create(name='male').pk
        post_data = {
            "name": "John Doe",
            # inline data
            "generic_inline_admin-phonenumber-content_type-object_id-TOTAL_FORMS": "1",
            "generic_inline_admin-phonenumber-content_type-object_id-INITIAL_FORMS": "0",
            "generic_inline_admin-phonenumber-content_type-object_id-MAX_NUM_FORMS": "0",
            "generic_inline_admin-phonenumber-content_type-object_id-0-id": "",
            "generic_inline_admin-phonenumber-content_type-object_id-0-phone_number": "555-555-5555",
            "generic_inline_admin-phonenumber-content_type-object_id-0-category": "%s" % category_id,
        }
        response = self.client.get('/generic_inline_admin/admin/generic_inline_admin/contact/add/')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/generic_inline_admin/admin/generic_inline_admin/contact/add/', post_data)
        self.assertEqual(response.status_code, 302) # redirect somewhere

class NoInlineDeletionTest(TestCase):
    urls = "regressiontests.generic_inline_admin.urls"

    def test_no_deletion(self):
        fake_site = object()
        inline = MediaPermanentInline(EpisodePermanent, fake_site)
        fake_request = object()
        formset = inline.get_formset(fake_request)
        self.assertFalse(formset.can_delete)


class MockRequest(object):
    pass

class MockSuperUser(object):
    def has_perm(self, perm):
        return True

request = MockRequest()
request.user = MockSuperUser()


class GenericInlineModelAdminTest(TestCase):
    urls = "regressiontests.generic_inline_admin.urls"

    def setUp(self):
        self.site = AdminSite()

    def test_get_formset_kwargs(self):
        media_inline = MediaInline(Media, AdminSite())

        # Create a formset with default arguments
        formset = media_inline.get_formset(request)
        self.assertEqual(formset.max_num, DEFAULT_MAX_NUM)
        self.assertEqual(formset.can_order, False)

        # Create a formset with custom keyword arguments
        formset = media_inline.get_formset(request, max_num=100, can_order=True)
        self.assertEqual(formset.max_num, 100)
        self.assertEqual(formset.can_order, True)

    def test_custom_form_meta_exclude_with_readonly(self):
        """
        Ensure that the custom ModelForm's `Meta.exclude` is respected when
        used in conjunction with `GenericInlineModelAdmin.readonly_fields`
        and when no `ModelAdmin.exclude` is defined.
        """
        class MediaForm(ModelForm):

            class Meta:
                model = Media
                exclude = ['url']

        class MediaInline(GenericTabularInline):
            readonly_fields = ['description']
            form = MediaForm
            model = Media

        class EpisodeAdmin(admin.ModelAdmin):
            inlines = [
                MediaInline
            ]

        ma = EpisodeAdmin(Episode, self.site)
        self.assertEqual(
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['keywords', 'id', 'DELETE'])

    def test_custom_form_meta_exclude(self):
        """
        Ensure that the custom ModelForm's `Meta.exclude` is respected by
        `GenericInlineModelAdmin.get_formset`, and overridden if
        `ModelAdmin.exclude` or `GenericInlineModelAdmin.exclude` are defined.
        Refs #15907.
        """
        # First with `GenericInlineModelAdmin`  -----------------

        class MediaForm(ModelForm):

            class Meta:
                model = Media
                exclude = ['url']

        class MediaInline(GenericTabularInline):
            exclude = ['description']
            form = MediaForm
            model = Media

        class EpisodeAdmin(admin.ModelAdmin):
            inlines = [
                MediaInline
            ]

        ma = EpisodeAdmin(Episode, self.site)
        self.assertEqual(
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['url', 'keywords', 'id', 'DELETE'])

        # Then, only with `ModelForm`  -----------------

        class MediaInline(GenericTabularInline):
            form = MediaForm
            model = Media

        class EpisodeAdmin(admin.ModelAdmin):
            inlines = [
                MediaInline
            ]

        ma = EpisodeAdmin(Episode, self.site)
        self.assertEqual(
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['description', 'keywords', 'id', 'DELETE'])

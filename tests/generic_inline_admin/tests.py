from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.forms.formsets import DEFAULT_MAX_NUM
from django.forms.models import ModelForm
from django.test import (
    RequestFactory, SimpleTestCase, TestCase, override_settings,
)
from django.urls import reverse

from .admin import MediaInline, MediaPermanentInline, site as admin_site
from .models import Category, Episode, EpisodePermanent, Media, PhoneNumber


class TestDataMixin:

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(username='super', password='secret', email='super@example.com')


@override_settings(ROOT_URLCONF='generic_inline_admin.urls')
class GenericAdminViewTest(TestDataMixin, TestCase):

    def setUp(self):
        self.client.force_login(self.superuser)

        e = Episode.objects.create(name='This Week in Django')
        self.episode_pk = e.pk
        m = Media(content_object=e, url='http://example.com/podcast.mp3')
        m.save()
        self.mp3_media_pk = m.pk

        m = Media(content_object=e, url='http://example.com/logo.png')
        m.save()
        self.png_media_pk = m.pk

    def test_basic_add_GET(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get(reverse('admin:generic_inline_admin_episode_add'))
        self.assertEqual(response.status_code, 200)

    def test_basic_edit_GET(self):
        """
        A smoke test to ensure GET on the change_view works.
        """
        response = self.client.get(
            reverse('admin:generic_inline_admin_episode_change', args=(self.episode_pk,))
        )
        self.assertEqual(response.status_code, 200)

    def test_basic_add_POST(self):
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
        response = self.client.post(reverse('admin:generic_inline_admin_episode_add'), post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere

    def test_basic_edit_POST(self):
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
        url = reverse('admin:generic_inline_admin_episode_change', args=(self.episode_pk,))
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere


@override_settings(ROOT_URLCONF='generic_inline_admin.urls')
class GenericInlineAdminParametersTest(TestDataMixin, TestCase):

    def setUp(self):
        self.client.force_login(self.superuser)
        self.factory = RequestFactory()

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

    def test_no_param(self):
        """
        With one initial form, extra (default) at 3, there should be 4 forms.
        """
        e = self._create_object(Episode)
        response = self.client.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 4)
        self.assertEqual(formset.initial_form_count(), 1)

    def test_extra_param(self):
        """
        With extra=0, there should be one form.
        """
        class ExtraInline(GenericTabularInline):
            model = Media
            extra = 0

        modeladmin = admin.ModelAdmin(Episode, admin_site)
        modeladmin.inlines = [ExtraInline]

        e = self._create_object(Episode)
        request = self.factory.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        request.user = User(username='super', is_superuser=True)
        response = modeladmin.changeform_view(request, object_id=str(e.pk))
        formset = response.context_data['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 1)
        self.assertEqual(formset.initial_form_count(), 1)

    def testMaxNumParam(self):
        """
        With extra=5 and max_num=2, there should be only 2 forms.
        """
        class MaxNumInline(GenericTabularInline):
            model = Media
            extra = 5
            max_num = 2

        modeladmin = admin.ModelAdmin(Episode, admin_site)
        modeladmin.inlines = [MaxNumInline]

        e = self._create_object(Episode)
        request = self.factory.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        request.user = User(username='super', is_superuser=True)
        response = modeladmin.changeform_view(request, object_id=str(e.pk))
        formset = response.context_data['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 2)
        self.assertEqual(formset.initial_form_count(), 1)

    def test_min_num_param(self):
        """
        With extra=3 and min_num=2, there should be five forms.
        """
        class MinNumInline(GenericTabularInline):
            model = Media
            extra = 3
            min_num = 2

        modeladmin = admin.ModelAdmin(Episode, admin_site)
        modeladmin.inlines = [MinNumInline]

        e = self._create_object(Episode)
        request = self.factory.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        request.user = User(username='super', is_superuser=True)
        response = modeladmin.changeform_view(request, object_id=str(e.pk))
        formset = response.context_data['inline_admin_formsets'][0].formset
        self.assertEqual(formset.total_form_count(), 5)
        self.assertEqual(formset.initial_form_count(), 1)

    def test_get_extra(self):

        class GetExtraInline(GenericTabularInline):
            model = Media
            extra = 4

            def get_extra(self, request, obj):
                return 2

        modeladmin = admin.ModelAdmin(Episode, admin_site)
        modeladmin.inlines = [GetExtraInline]
        e = self._create_object(Episode)
        request = self.factory.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        request.user = User(username='super', is_superuser=True)
        response = modeladmin.changeform_view(request, object_id=str(e.pk))
        formset = response.context_data['inline_admin_formsets'][0].formset

        self.assertEqual(formset.extra, 2)

    def test_get_min_num(self):

        class GetMinNumInline(GenericTabularInline):
            model = Media
            min_num = 5

            def get_min_num(self, request, obj):
                return 2

        modeladmin = admin.ModelAdmin(Episode, admin_site)
        modeladmin.inlines = [GetMinNumInline]
        e = self._create_object(Episode)
        request = self.factory.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        request.user = User(username='super', is_superuser=True)
        response = modeladmin.changeform_view(request, object_id=str(e.pk))
        formset = response.context_data['inline_admin_formsets'][0].formset

        self.assertEqual(formset.min_num, 2)

    def test_get_max_num(self):

        class GetMaxNumInline(GenericTabularInline):
            model = Media
            extra = 5

            def get_max_num(self, request, obj):
                return 2

        modeladmin = admin.ModelAdmin(Episode, admin_site)
        modeladmin.inlines = [GetMaxNumInline]
        e = self._create_object(Episode)
        request = self.factory.get(reverse('admin:generic_inline_admin_episode_change', args=(e.pk,)))
        request.user = User(username='super', is_superuser=True)
        response = modeladmin.changeform_view(request, object_id=str(e.pk))
        formset = response.context_data['inline_admin_formsets'][0].formset

        self.assertEqual(formset.max_num, 2)


@override_settings(ROOT_URLCONF='generic_inline_admin.urls')
class GenericInlineAdminWithUniqueTogetherTest(TestDataMixin, TestCase):

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_add(self):
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
        response = self.client.get(reverse('admin:generic_inline_admin_contact_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('admin:generic_inline_admin_contact_add'), post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere

    def test_delete(self):
        from .models import Contact
        c = Contact.objects.create(name='foo')
        PhoneNumber.objects.create(
            object_id=c.id,
            content_type=ContentType.objects.get_for_model(Contact),
            phone_number="555-555-5555",
        )
        response = self.client.post(reverse('admin:generic_inline_admin_contact_delete', args=[c.pk]))
        self.assertContains(response, 'Are you sure you want to delete')


@override_settings(ROOT_URLCONF='generic_inline_admin.urls')
class NoInlineDeletionTest(SimpleTestCase):

    def test_no_deletion(self):
        inline = MediaPermanentInline(EpisodePermanent, admin_site)
        fake_request = object()
        formset = inline.get_formset(fake_request)
        self.assertFalse(formset.can_delete)


class MockRequest:
    pass


class MockSuperUser:
    def has_perm(self, perm):
        return True


request = MockRequest()
request.user = MockSuperUser()


@override_settings(ROOT_URLCONF='generic_inline_admin.urls')
class GenericInlineModelAdminTest(SimpleTestCase):

    def setUp(self):
        self.site = AdminSite()

    def test_get_formset_kwargs(self):
        media_inline = MediaInline(Media, AdminSite())

        # Create a formset with default arguments
        formset = media_inline.get_formset(request)
        self.assertEqual(formset.max_num, DEFAULT_MAX_NUM)
        self.assertIs(formset.can_order, False)

        # Create a formset with custom keyword arguments
        formset = media_inline.get_formset(request, max_num=100, can_order=True)
        self.assertEqual(formset.max_num, 100)
        self.assertIs(formset.can_order, True)

    def test_custom_form_meta_exclude_with_readonly(self):
        """
        The custom ModelForm's `Meta.exclude` is respected when
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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['keywords', 'id', 'DELETE'])

    def test_custom_form_meta_exclude(self):
        """
        The custom ModelForm's `Meta.exclude` is respected by
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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['description', 'keywords', 'id', 'DELETE'])

    def test_get_fieldsets(self):
        # get_fieldsets is called when figuring out form fields.
        # Refs #18681.
        class MediaForm(ModelForm):
            class Meta:
                model = Media
                fields = '__all__'

        class MediaInline(GenericTabularInline):
            form = MediaForm
            model = Media
            can_delete = False

            def get_fieldsets(self, request, obj=None):
                return [(None, {'fields': ['url', 'description']})]

        ma = MediaInline(Media, self.site)
        form = ma.get_formset(None).form
        self.assertEqual(form._meta.fields, ['url', 'description'])

    def test_get_formsets_with_inlines_returns_tuples(self):
        """
        get_formsets_with_inlines() returns the correct tuples.
        """
        class MediaForm(ModelForm):
            class Meta:
                model = Media
                exclude = ['url']

        class MediaInline(GenericTabularInline):
            form = MediaForm
            model = Media

        class AlternateInline(GenericTabularInline):
            form = MediaForm
            model = Media

        class EpisodeAdmin(admin.ModelAdmin):
            inlines = [
                AlternateInline, MediaInline
            ]
        ma = EpisodeAdmin(Episode, self.site)
        inlines = ma.get_inline_instances(request)
        for (formset, inline), other_inline in zip(ma.get_formsets_with_inlines(request), inlines):
            self.assertIsInstance(formset, other_inline.get_formset(request).__class__)

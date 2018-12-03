from datetime import date

from django.contrib.admin.options import ModelAdmin, TabularInline
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils.deprecation import RemovedInDjango30Warning

from .models import Band, Song
from .test_checks import CheckTestCase


class HasAddPermissionObjTests(CheckTestCase):
    def test_model_admin_inherited_valid(self):
        class BandAdmin(ModelAdmin):
            pass

        self.assertIsValid(BandAdmin, Band)

    def test_model_admin_valid(self):
        class BandAdmin(ModelAdmin):
            def has_add_permission(self, request):
                return super().has_add_permission(request)

        self.assertIsValid(BandAdmin, Band)

    def test_inline_admin_inherited_valid(self):
        class SongInlineAdmin(TabularInline):
            model = Song

        class BandAdmin(ModelAdmin):
            inlines = [SongInlineAdmin]

        self.assertIsValid(BandAdmin, Band)

    def test_inline_admin_valid(self):
        class SongInlineAdmin(TabularInline):
            model = Song

            def has_add_permission(self, request, obj):
                return super().has_add_permission(request, obj)

        class BandAdmin(ModelAdmin):
            inlines = [SongInlineAdmin]

        self.assertIsValid(BandAdmin, Band)

    def test_inline_admin_warning(self):
        class SongInlineAdmin(TabularInline):
            model = Song

            def has_add_permission(self, request):
                return super().has_add_permission(request)

        class BandAdmin(ModelAdmin):
            inlines = [SongInlineAdmin]

        msg = (
            "Update SongInlineAdmin.has_add_permission() to accept a "
            "positional `obj` argument."
        )
        with self.assertWarnsMessage(RemovedInDjango30Warning, msg):
            self.assertIsValid(BandAdmin, Band)


class MockRequest:
    method = 'POST'
    FILES = {}
    POST = {}


class SongInline(TabularInline):
    model = Song

    def has_add_permission(self, request):
        return True


class BandAdmin(ModelAdmin):
    inlines = [SongInline]


class ModelAdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.band = Band.objects.create(name='The Doors', bio='', sign_date=date(1965, 1, 1))
        cls.song = Song.objects.create(name='test', band=cls.band)

    def setUp(self):
        self.site = AdminSite()
        self.request = MockRequest()
        self.request.POST = {
            'song_set-TOTAL_FORMS': 4,
            'song_set-INITIAL_FORMS': 1,
        }
        self.request.user = self.MockAddUser()
        self.ma = BandAdmin(Band, self.site)

    class MockAddUser:
        def has_perm(self, perm):
            return perm == 'modeladmin.add_band'

    def test_get_inline_instances(self):
        self.assertEqual(len(self.ma.get_inline_instances(self.request)), 1)

    def test_get_inline_formsets(self):
        formsets, inline_instances = self.ma._create_formsets(self.request, self.band, change=True)
        self.assertEqual(len(self.ma.get_inline_formsets(self.request, formsets, inline_instances)), 1)

    def test_get_formsets_with_inlines(self):
        self.assertEqual(len(list(self.ma. get_formsets_with_inlines(self.request, self.band))), 1)

from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.test import RequestFactory, TestCase

from .models import (
    Band,
    DynOrderingBandAdmin,
    ReportData,
    Song,
    SongInlineDefaultOrdering,
    SongInlineNewOrdering,
    SystemUser,
    UserPermission,
)


class MockRequest:
    pass


class MockSuperUser:
    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, module):
        return True


request = MockRequest()
request.user = MockSuperUser()

site = admin.AdminSite()


class TestAdminOrdering(TestCase):
    """
    Let's make sure that ModelAdmin.get_queryset uses the ordering we define
    in ModelAdmin rather that ordering defined in the model's inner Meta
    class.
    """

    request_factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        Band.objects.bulk_create(
            [
                Band(name="Aerosmith", bio="", rank=3),
                Band(name="Radiohead", bio="", rank=1),
                Band(name="Van Halen", bio="", rank=2),
            ]
        )

    def test_default_ordering(self):
        """
        The default ordering should be by name, as specified in the inner Meta
        class.
        """
        ma = ModelAdmin(Band, site)
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(["Aerosmith", "Radiohead", "Van Halen"], names)

    def test_specified_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering, and make sure
        it actually changes.
        """

        class BandAdmin(ModelAdmin):
            ordering = ("rank",)  # default ordering is ('name',)

        ma = BandAdmin(Band, site)
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(["Radiohead", "Van Halen", "Aerosmith"], names)

    def test_specified_ordering_by_f_expression(self):
        class BandAdmin(ModelAdmin):
            ordering = (F("rank").desc(nulls_last=True),)

        band_admin = BandAdmin(Band, site)
        names = [b.name for b in band_admin.get_queryset(request)]
        self.assertEqual(["Aerosmith", "Van Halen", "Radiohead"], names)

    def test_dynamic_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering dynamically.
        """
        super_user = User.objects.create(username="admin", is_superuser=True)
        other_user = User.objects.create(username="other")
        request = self.request_factory.get("/")
        request.user = super_user
        ma = DynOrderingBandAdmin(Band, site)
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(["Radiohead", "Van Halen", "Aerosmith"], names)
        request.user = other_user
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(["Aerosmith", "Radiohead", "Van Halen"], names)


class TestInlineModelAdminOrdering(TestCase):
    """
    Let's make sure that InlineModelAdmin.get_queryset uses the ordering we
    define in InlineModelAdmin.
    """

    @classmethod
    def setUpTestData(cls):
        cls.band = Band.objects.create(name="Aerosmith", bio="", rank=3)
        Song.objects.bulk_create(
            [
                Song(band=cls.band, name="Pink", duration=235),
                Song(band=cls.band, name="Dude (Looks Like a Lady)", duration=264),
                Song(band=cls.band, name="Jaded", duration=214),
            ]
        )

    def test_default_ordering(self):
        """
        The default ordering should be by name, as specified in the inner Meta
        class.
        """
        inline = SongInlineDefaultOrdering(self.band, site)
        names = [s.name for s in inline.get_queryset(request)]
        self.assertEqual(["Dude (Looks Like a Lady)", "Jaded", "Pink"], names)

    def test_specified_ordering(self):
        """
        Let's check with ordering set to something different than the default.
        """
        inline = SongInlineNewOrdering(self.band, site)
        names = [s.name for s in inline.get_queryset(request)]
        self.assertEqual(["Jaded", "Pink", "Dude (Looks Like a Lady)"], names)


class TestRelatedFieldsAdminOrdering(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.b1 = Band.objects.create(name="Pink Floyd", bio="", rank=1)
        cls.b2 = Band.objects.create(name="Foo Fighters", bio="", rank=5)

    def setUp(self):
        # we need to register a custom ModelAdmin (instead of just using
        # ModelAdmin) because the field creator tries to find the ModelAdmin
        # for the related model
        class SongAdmin(admin.ModelAdmin):
            pass

        site.register(Song, SongAdmin)

    def tearDown(self):
        site.unregister(Song)
        if site.is_registered(Band):
            site.unregister(Band)

    def check_ordering_of_field_choices(self, correct_ordering):
        fk_field = site.get_model_admin(Song).formfield_for_foreignkey(
            Song.band.field, request=None
        )
        m2m_field = site.get_model_admin(Song).formfield_for_manytomany(
            Song.other_interpreters.field, request=None
        )
        self.assertEqual(list(fk_field.queryset), correct_ordering)
        self.assertEqual(list(m2m_field.queryset), correct_ordering)

    def test_no_admin_fallback_to_model_ordering(self):
        # should be ordered by name (as defined by the model)
        self.check_ordering_of_field_choices([self.b2, self.b1])

    def test_admin_with_no_ordering_fallback_to_model_ordering(self):
        class NoOrderingBandAdmin(admin.ModelAdmin):
            pass

        site.register(Band, NoOrderingBandAdmin)

        # should be ordered by name (as defined by the model)
        self.check_ordering_of_field_choices([self.b2, self.b1])

    def test_admin_ordering_beats_model_ordering(self):
        class StaticOrderingBandAdmin(admin.ModelAdmin):
            ordering = ("rank",)

        site.register(Band, StaticOrderingBandAdmin)

        # should be ordered by rank (defined by the ModelAdmin)
        self.check_ordering_of_field_choices([self.b1, self.b2])

    def test_custom_queryset_still_wins(self):
        """Custom queryset has still precedence (#21405)"""

        class SongAdmin(admin.ModelAdmin):
            # Exclude one of the two Bands from the querysets
            def formfield_for_foreignkey(self, db_field, request, **kwargs):
                if db_field.name == "band":
                    kwargs["queryset"] = Band.objects.filter(rank__gt=2)
                return super().formfield_for_foreignkey(db_field, request, **kwargs)

            def formfield_for_manytomany(self, db_field, request, **kwargs):
                if db_field.name == "other_interpreters":
                    kwargs["queryset"] = Band.objects.filter(rank__gt=2)
                return super().formfield_for_foreignkey(db_field, request, **kwargs)

        class StaticOrderingBandAdmin(admin.ModelAdmin):
            ordering = ("rank",)

        site.unregister(Song)
        site.register(Song, SongAdmin)
        site.register(Band, StaticOrderingBandAdmin)

        self.check_ordering_of_field_choices([self.b2])


class TestCustomAdminOrdering(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create permissions
        perm1 = UserPermission.objects.create(permission="Permission 1")
        perm2 = UserPermission.objects.create(permission="Permission 2")
        perm3 = UserPermission.objects.create(permission="Permission 3")

        # Create users with permissions
        cls.user1 = SystemUser.objects.create(name="User 1")
        cls.user2 = SystemUser.objects.create(name="User 2")

        cls.user1.permissions.add(perm1, perm2)
        cls.user2.permissions.add(perm1, perm2, perm3)

        # Register Admin classes
        class UserAdmin(admin.ModelAdmin):
            ordering = ["-permissions__count"]

            def get_queryset(self, request):
                qs = super().get_queryset(request)
                return qs.annotate(permissions__count=models.Count("permissions"))

        class ReportAdmin(admin.ModelAdmin):
            pass

        admin.site.register(SystemUser, UserAdmin)
        admin.site.register(ReportData, ReportAdmin)

    def test_system_user_ordering(self):
        #Test if the ordering for SystemUser Admin is as expected
        fk_field = admin.site._registry[ReportData].formfield_for_foreignkey(
            ReportData.owner.field, request=None
        )
        expected_order = [self.user2, self.user1]  # Ordering by permissions
        self.assertEqual(list(fk_field.queryset), expected_order)

from __future__ import absolute_import, unicode_literals

from django.test import TestCase, RequestFactory
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.contrib.auth.models import User

from .models import (Band, Song, SongInlineDefaultOrdering,
    SongInlineNewOrdering, DynOrderingBandAdmin)


class MockRequest(object):
    pass

class MockSuperUser(object):
    def has_perm(self, perm):
        return True

request = MockRequest()
request.user = MockSuperUser()


class TestAdminOrdering(TestCase):
    """
    Let's make sure that ModelAdmin.get_queryset uses the ordering we define
    in ModelAdmin rather that ordering defined in the model's inner Meta
    class.
    """

    def setUp(self):
        self.request_factory = RequestFactory()
        b1 = Band(name='Aerosmith', bio='', rank=3)
        b1.save()
        b2 = Band(name='Radiohead', bio='', rank=1)
        b2.save()
        b3 = Band(name='Van Halen', bio='', rank=2)
        b3.save()

    def test_default_ordering(self):
        """
        The default ordering should be by name, as specified in the inner Meta
        class.
        """
        ma = ModelAdmin(Band, None)
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(['Aerosmith', 'Radiohead', 'Van Halen'], names)

    def test_specified_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering, and make sure
        it actually changes.
        """
        class BandAdmin(ModelAdmin):
            ordering = ('rank',) # default ordering is ('name',)
        ma = BandAdmin(Band, None)
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(['Radiohead', 'Van Halen', 'Aerosmith'], names)

    def test_dynamic_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering dinamically.
        """
        super_user = User.objects.create(username='admin', is_superuser=True)
        other_user = User.objects.create(username='other')
        request = self.request_factory.get('/')
        request.user = super_user
        ma = DynOrderingBandAdmin(Band, None)
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(['Radiohead', 'Van Halen', 'Aerosmith'], names)
        request.user = other_user
        names = [b.name for b in ma.get_queryset(request)]
        self.assertEqual(['Aerosmith', 'Radiohead', 'Van Halen'], names)


class TestInlineModelAdminOrdering(TestCase):
    """
    Let's make sure that InlineModelAdmin.get_queryset uses the ordering we
    define in InlineModelAdmin.
    """

    def setUp(self):
        b = Band(name='Aerosmith', bio='', rank=3)
        b.save()
        self.b = b
        s1 = Song(band=b, name='Pink', duration=235)
        s1.save()
        s2 = Song(band=b, name='Dude (Looks Like a Lady)', duration=264)
        s2.save()
        s3 = Song(band=b, name='Jaded', duration=214)
        s3.save()

    def test_default_ordering(self):
        """
        The default ordering should be by name, as specified in the inner Meta
        class.
        """
        inline = SongInlineDefaultOrdering(self.b, None)
        names = [s.name for s in inline.get_queryset(request)]
        self.assertEqual(['Dude (Looks Like a Lady)', 'Jaded', 'Pink'], names)

    def test_specified_ordering(self):
        """
        Let's check with ordering set to something different than the default.
        """
        inline = SongInlineNewOrdering(self.b, None)
        names = [s.name for s in inline.get_queryset(request)]
        self.assertEqual(['Jaded', 'Pink', 'Dude (Looks Like a Lady)'], names)


class TestRelatedFieldsAdminOrdering(TestCase):
    def setUp(self):
        self.b1 = Band(name='Pink Floyd', bio='', rank=1)
        self.b1.save()
        self.b2 = Band(name='Foo Fighters', bio='', rank=5)
        self.b2.save()

        # we need to register a custom ModelAdmin (instead of just using
        # ModelAdmin) because the field creator tries to find the ModelAdmin
        # for the related model
        class SongAdmin(admin.ModelAdmin):
            pass
        admin.site.register(Song, SongAdmin)

    def check_ordering_of_field_choices(self, correct_ordering):
        fk_field = admin.site._registry[Song].formfield_for_foreignkey(Song.band.field)
        m2m_field = admin.site._registry[Song].formfield_for_manytomany(Song.other_interpreters.field)

        self.assertEqual(list(fk_field.queryset), correct_ordering)
        self.assertEqual(list(m2m_field.queryset), correct_ordering)

    def test_no_admin_fallback_to_model_ordering(self):
        # should be ordered by name (as defined by the model)
        self.check_ordering_of_field_choices([self.b2, self.b1])

    def test_admin_with_no_ordering_fallback_to_model_ordering(self):
        class NoOrderingBandAdmin(admin.ModelAdmin):
            pass
        admin.site.register(Band, NoOrderingBandAdmin)

        # should be ordered by name (as defined by the model)
        self.check_ordering_of_field_choices([self.b2, self.b1])

    def test_admin_ordering_beats_model_ordering(self):
        class StaticOrderingBandAdmin(admin.ModelAdmin):
            ordering = ('rank', )
        admin.site.register(Band, StaticOrderingBandAdmin)

        # should be ordered by rank (defined by the ModelAdmin)
        self.check_ordering_of_field_choices([self.b1, self.b2])

    def tearDown(self):
        admin.site.unregister(Song)
        if Band in admin.site._registry:
            admin.site.unregister(Band)

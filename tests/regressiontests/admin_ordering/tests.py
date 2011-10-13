from __future__ import absolute_import

from django.test import TestCase, RequestFactory
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
    Let's make sure that ModelAdmin.queryset uses the ordering we define in
    ModelAdmin rather that ordering defined in the model's inner Meta
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
        names = [b.name for b in ma.queryset(request)]
        self.assertEqual([u'Aerosmith', u'Radiohead', u'Van Halen'], names)

    def test_specified_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering, and make sure
        it actually changes.
        """
        class BandAdmin(ModelAdmin):
            ordering = ('rank',) # default ordering is ('name',)
        ma = BandAdmin(Band, None)
        names = [b.name for b in ma.queryset(request)]
        self.assertEqual([u'Radiohead', u'Van Halen', u'Aerosmith'], names)

    def test_dynamic_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering dinamically.
        """
        super_user = User.objects.create(username='admin', is_superuser=True)
        other_user = User.objects.create(username='other')
        request = self.request_factory.get('/')
        request.user = super_user
        ma = DynOrderingBandAdmin(Band, None)
        names = [b.name for b in ma.queryset(request)]
        self.assertEqual([u'Radiohead', u'Van Halen', u'Aerosmith'], names)
        request.user = other_user
        names = [b.name for b in ma.queryset(request)]
        self.assertEqual([u'Aerosmith', u'Radiohead', u'Van Halen'], names)


class TestInlineModelAdminOrdering(TestCase):
    """
    Let's make sure that InlineModelAdmin.queryset uses the ordering we define
    in InlineModelAdmin.
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
        names = [s.name for s in inline.queryset(request)]
        self.assertEqual([u'Dude (Looks Like a Lady)', u'Jaded', u'Pink'], names)

    def test_specified_ordering(self):
        """
        Let's check with ordering set to something different than the default.
        """
        inline = SongInlineNewOrdering(self.b, None)
        names = [s.name for s in inline.queryset(request)]
        self.assertEqual([u'Jaded', u'Pink', u'Dude (Looks Like a Lady)'], names)

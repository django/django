from django.test import TestCase
from django.contrib.admin.options import ModelAdmin

from models import Band

class TestAdminOrdering(TestCase):
    """
    Let's make sure that ModelAdmin.queryset uses the ordering we define in
    ModelAdmin rather that ordering defined in the model's inner Meta
    class.
    """

    def setUp(self):
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
        names = [b.name for b in ma.queryset(None)]
        self.assertEqual([u'Aerosmith', u'Radiohead', u'Van Halen'], names)

    def test_specified_ordering(self):
        """
        Let's use a custom ModelAdmin that changes the ordering, and make sure
        it actually changes.
        """
        class BandAdmin(ModelAdmin):
            ordering = ('rank',) # default ordering is ('name',)
        ma = BandAdmin(Band, None)
        names = [b.name for b in ma.queryset(None)]
        self.assertEqual([u'Radiohead', u'Van Halen', u'Aerosmith'], names)

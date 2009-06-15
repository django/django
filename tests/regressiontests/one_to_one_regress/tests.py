from django.test import TestCase
from regressiontests.one_to_one_regress.models import Place, UndergroundBar

class OneToOneDeletionTests(TestCase):
    def test_reverse_relationship_cache_cascade(self):
        """
        Regression test for #9023: accessing the reverse relationship shouldn't
        result in a cascading delete().
        """
        place = Place.objects.create(name="Dempsey's", address="623 Vermont St")
        bar = UndergroundBar.objects.create(place=place, serves_cocktails=False)

        # The bug in #9023: if you access the one-to-one relation *before*
        # setting to None and deleting, the cascade happens anyway.
        place.undergroundbar
        bar.place.name='foo'
        bar.place = None
        bar.save()
        place.delete()

        self.assertEqual(Place.objects.all().count(), 0)
        self.assertEqual(UndergroundBar.objects.all().count(), 1)

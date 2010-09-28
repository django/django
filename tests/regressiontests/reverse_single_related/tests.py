from django.test import TestCase

from regressiontests.reverse_single_related.models import *

class ReverseSingleRelatedTests(TestCase):
    """
    Regression tests for an object that cannot access a single related
    object due to a restrictive default manager.
    """

    def test_reverse_single_related(self):

        public_source = Source.objects.create(is_public=True)
        public_item = Item.objects.create(source=public_source)

        private_source = Source.objects.create(is_public=False)
        private_item = Item.objects.create(source=private_source)

        # Only one source is available via all() due to the custom default manager.
        self.assertQuerysetEqual(
                Source.objects.all(),
                ["<Source: Source object>"]
        )

        self.assertEquals(public_item.source, public_source)

        # Make sure that an item can still access its related source even if the default
        # manager doesn't normally allow it.
        self.assertEquals(private_item.source, private_source)

        # If the manager is marked "use_for_related_fields", it'll get used instead
        # of the "bare" queryset. Usually you'd define this as a property on the class,
        # but this approximates that in a way that's easier in tests.
        Source.objects.use_for_related_fields = True
        private_item = Item.objects.get(pk=private_item.pk)
        self.assertRaises(Source.DoesNotExist, lambda: private_item.source)

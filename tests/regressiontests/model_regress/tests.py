from models import Worker
from django.test import TestCase

class RelatedModelOrderedLookupTest(TestCase):
    """
    Regression test for #10153: foreign key __gte and __lte lookups.
    """
    
    # The bug is that the following queries would raise:
    # "TypeError: Related Field has invalid lookup: gte"
    
    def test_related_gte_lookup(self):
        Worker.objects.filter(department__gte=0)

    def test_related_lte_lookup(self):
        Worker.objects.filter(department__lte=0)

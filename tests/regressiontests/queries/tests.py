import unittest
from models import Tag, Annotation
from django.db.models import Count

class QuerysetOrderedTests(unittest.TestCase):
    """
    Tests for the Queryset.ordered attribute.
    """
    
    def test_no_default_or_explicit_ordering(self):
        self.assertEqual(Annotation.objects.all().ordered, False)

    def test_cleared_default_ordering(self):
        self.assertEqual(Tag.objects.all().ordered, True)
        self.assertEqual(Tag.objects.all().order_by().ordered, False)
        
    def test_explicit_ordering(self):
        self.assertEqual(Annotation.objects.all().order_by('id').ordered, True)
        
    def test_order_by_extra(self):
        self.assertEqual(Annotation.objects.all().extra(order_by=['id']).ordered, True)
        
    def test_annotated_ordering(self):
        qs = Annotation.objects.annotate(num_notes=Count('notes'))
        self.assertEqual(qs.ordered, False)
        self.assertEqual(qs.order_by('num_notes').ordered, True)
        
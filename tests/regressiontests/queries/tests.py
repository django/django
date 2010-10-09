import unittest

from django.db import DatabaseError, connections, DEFAULT_DB_ALIAS
from django.db.models import Count
from django.test import TestCase

from models import Tag, Annotation, DumbCategory, Note, ExtraInfo, Number

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


class SubqueryTests(TestCase):
    def setUp(self):
        DumbCategory.objects.create(id=1)
        DumbCategory.objects.create(id=2)
        DumbCategory.objects.create(id=3)

    def test_ordered_subselect(self):
        "Subselects honor any manual ordering"
        try:
            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:2])
            self.assertEquals(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[:2])
            self.assertEquals(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[2:])
            self.assertEquals(set(query.values_list('id', flat=True)), set([1]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connections[DEFAULT_DB_ALIAS].features.allow_sliced_subqueries)

    def test_sliced_delete(self):
        "Delete queries can safely contain sliced subqueries"
        try:
            DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:1]).delete()
            self.assertEquals(set(DumbCategory.objects.values_list('id', flat=True)), set([1,2]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connections[DEFAULT_DB_ALIAS].features.allow_sliced_subqueries)

class CloneTests(TestCase):
    def test_evaluated_queryset_as_argument(self):
        "#13227 -- If a queryset is already evaluated, it can still be used as a query arg"
        n = Note(note='Test1', misc='misc')
        n.save()
        e = ExtraInfo(info='good', note=n)
        e.save()

        n_list = Note.objects.all()
        # Evaluate the Note queryset, populating the query cache
        list(n_list)
        # Use the note queryset in a query, and evalute
        # that query in a way that involves cloning.
        try:
            self.assertEquals(ExtraInfo.objects.filter(note__in=n_list)[0].info, 'good')
        except:
            self.fail('Query should be clonable')


class EmptyQuerySetTests(TestCase):
    def test_emptyqueryset_values(self):
        "#14366 -- calling .values() on an EmptyQuerySet and then cloning that should not cause an error"
        self.assertEqual(list(Number.objects.none().values('num').order_by('num')), [])

from django.db.models import F, IntegerField, Value
from django.db.utils import DatabaseError, NotSupportedError
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import Number, ReservedName


@skipUnlessDBFeature('supports_select_union')
class QuerySetSetOperationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Number.objects.bulk_create(Number(num=i) for i in range(10))

    def number_transform(self, value):
        return value.num

    def assertNumbersEqual(self, queryset, expected_numbers, ordered=True):
        self.assertQuerysetEqual(queryset, expected_numbers, self.number_transform, ordered)

    def test_simple_union(self):
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=8)
        qs3 = Number.objects.filter(num=5)
        self.assertNumbersEqual(qs1.union(qs2, qs3), [0, 1, 5, 8, 9], ordered=False)

    @skipUnlessDBFeature('supports_select_intersection')
    def test_simple_intersection(self):
        qs1 = Number.objects.filter(num__lte=5)
        qs2 = Number.objects.filter(num__gte=5)
        qs3 = Number.objects.filter(num__gte=4, num__lte=6)
        self.assertNumbersEqual(qs1.intersection(qs2, qs3), [5], ordered=False)

    @skipUnlessDBFeature('supports_select_difference')
    def test_simple_difference(self):
        qs1 = Number.objects.filter(num__lte=5)
        qs2 = Number.objects.filter(num__lte=4)
        self.assertNumbersEqual(qs1.difference(qs2), [5], ordered=False)

    def test_union_distinct(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        self.assertEqual(len(list(qs1.union(qs2, all=True))), 20)
        self.assertEqual(len(list(qs1.union(qs2))), 10)

    @skipUnlessDBFeature('supports_select_intersection')
    def test_intersection_with_empty_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.none()
        qs3 = Number.objects.filter(pk__in=[])
        self.assertEqual(len(qs1.intersection(qs2)), 0)
        self.assertEqual(len(qs1.intersection(qs3)), 0)
        self.assertEqual(len(qs2.intersection(qs1)), 0)
        self.assertEqual(len(qs3.intersection(qs1)), 0)
        self.assertEqual(len(qs2.intersection(qs2)), 0)
        self.assertEqual(len(qs3.intersection(qs3)), 0)

    @skipUnlessDBFeature('supports_select_difference')
    def test_difference_with_empty_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.none()
        qs3 = Number.objects.filter(pk__in=[])
        self.assertEqual(len(qs1.difference(qs2)), 10)
        self.assertEqual(len(qs1.difference(qs3)), 10)
        self.assertEqual(len(qs2.difference(qs1)), 0)
        self.assertEqual(len(qs3.difference(qs1)), 0)
        self.assertEqual(len(qs2.difference(qs2)), 0)
        self.assertEqual(len(qs3.difference(qs3)), 0)

    def test_union_with_empty_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.none()
        qs3 = Number.objects.filter(pk__in=[])
        self.assertEqual(len(qs1.union(qs2)), 10)
        self.assertEqual(len(qs2.union(qs1)), 10)
        self.assertEqual(len(qs1.union(qs3)), 10)
        self.assertEqual(len(qs3.union(qs1)), 10)
        self.assertEqual(len(qs2.union(qs1, qs1, qs1)), 10)
        self.assertEqual(len(qs2.union(qs1, qs1, all=True)), 20)
        self.assertEqual(len(qs2.union(qs2)), 0)
        self.assertEqual(len(qs3.union(qs3)), 0)

    def test_limits(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        self.assertEqual(len(list(qs1.union(qs2)[:2])), 2)

    def test_ordering(self):
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=2, num__lte=3)
        self.assertNumbersEqual(qs1.union(qs2).order_by('-num'), [3, 2, 1, 0])

    @skipUnlessDBFeature('supports_slicing_ordering_in_compound')
    def test_ordering_subqueries(self):
        qs1 = Number.objects.order_by('num')[:2]
        qs2 = Number.objects.order_by('-num')[:2]
        self.assertNumbersEqual(qs1.union(qs2).order_by('-num')[:4], [9, 8, 1, 0])

    @skipIfDBFeature('supports_slicing_ordering_in_compound')
    def test_unsupported_ordering_slicing_raises_db_error(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        msg = 'LIMIT/OFFSET not allowed in subqueries of compound statements'
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2[:10]))
        msg = 'ORDER BY not allowed in subqueries of compound statements'
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.order_by('id').union(qs2))

    @skipIfDBFeature('supports_select_intersection')
    def test_unsupported_intersection_raises_db_error(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        msg = 'intersection is not supported on this database backend'
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(qs1.intersection(qs2))

    def test_combining_multiple_models(self):
        ReservedName.objects.create(name='99 little bugs', order=99)
        qs1 = Number.objects.filter(num=1).values_list('num', flat=True)
        qs2 = ReservedName.objects.values_list('order')
        self.assertEqual(list(qs1.union(qs2).order_by('num')), [1, 99])

    def test_order_raises_on_non_selected_column(self):
        qs1 = Number.objects.filter().annotate(
            annotation=Value(1, IntegerField()),
        ).values('annotation', num2=F('num'))
        qs2 = Number.objects.filter().values('id', 'num')
        # Should not raise
        list(qs1.union(qs2).order_by('annotation'))
        list(qs1.union(qs2).order_by('num2'))
        msg = 'ORDER BY term does not match any column in the result set'
        # 'id' is not part of the select
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by('id'))
        # 'num' got realiased to num2
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by('num'))
        # switched order, now 'exists' again:
        list(qs2.union(qs1).order_by('num'))

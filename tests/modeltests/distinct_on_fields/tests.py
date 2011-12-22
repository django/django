from __future__ import absolute_import, with_statement

from django.db.models import Max
from django.test import TestCase, skipUnlessDBFeature

from .models import Tag, Celebrity, Fan, Staff, StaffTag

class DistinctOnTests(TestCase):
    def setUp(self):
        t1 = Tag.objects.create(name='t1')
        t2 = Tag.objects.create(name='t2', parent=t1)
        t3 = Tag.objects.create(name='t3', parent=t1)
        t4 = Tag.objects.create(name='t4', parent=t3)
        t5 = Tag.objects.create(name='t5', parent=t3)

        p1_o1 = Staff.objects.create(id=1, name="p1", organisation="o1")
        p2_o1 = Staff.objects.create(id=2, name="p2", organisation="o1")
        p3_o1 = Staff.objects.create(id=3, name="p3", organisation="o1")
        p1_o2 = Staff.objects.create(id=4, name="p1", organisation="o2")
        p1_o1.coworkers.add(p2_o1, p3_o1)
        StaffTag.objects.create(staff=p1_o1, tag=t1)
        StaffTag.objects.create(staff=p1_o1, tag=t1)

        celeb1 = Celebrity.objects.create(name="c1")
        celeb2 = Celebrity.objects.create(name="c2")

        self.fan1 = Fan.objects.create(fan_of=celeb1)
        self.fan2 = Fan.objects.create(fan_of=celeb1)
        self.fan3 = Fan.objects.create(fan_of=celeb2)

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_basic_distinct_on(self):
        """QuerySet.distinct('field', ...) works"""
        # (qset, expected) tuples
        qsets = (
            (
                Staff.objects.distinct().order_by('name'),
                ['<Staff: p1>', '<Staff: p1>', '<Staff: p2>', '<Staff: p3>'],
            ),
            (
                Staff.objects.distinct('name').order_by('name'),
                ['<Staff: p1>', '<Staff: p2>', '<Staff: p3>'],
            ),
            (
                Staff.objects.distinct('organisation').order_by('organisation', 'name'),
                ['<Staff: p1>', '<Staff: p1>'],
            ),
            (
                Staff.objects.distinct('name', 'organisation').order_by('name', 'organisation'),
                ['<Staff: p1>', '<Staff: p1>', '<Staff: p2>', '<Staff: p3>'],
            ),
            (
                Celebrity.objects.filter(fan__in=[self.fan1, self.fan2, self.fan3]).\
                    distinct('name').order_by('name'),
                ['<Celebrity: c1>', '<Celebrity: c2>'],
            ),
            # Does combining querysets work?
            (
                (Celebrity.objects.filter(fan__in=[self.fan1, self.fan2]).\
                    distinct('name').order_by('name')
                |Celebrity.objects.filter(fan__in=[self.fan3]).\
                    distinct('name').order_by('name')),
                ['<Celebrity: c1>', '<Celebrity: c2>'],
            ),
            (
                StaffTag.objects.distinct('staff','tag'),
                ['<StaffTag: t1 -> p1>'],
            ),
            (
                Tag.objects.order_by('parent__pk', 'pk').distinct('parent'),
                ['<Tag: t2>', '<Tag: t4>', '<Tag: t1>'],
            ),
            (
                StaffTag.objects.select_related('staff').distinct('staff__name').order_by('staff__name'),
                ['<StaffTag: t1 -> p1>'],
            ),
            # Fetch the alphabetically first coworker for each worker
            (
                (Staff.objects.distinct('id').order_by('id', 'coworkers__name').
                               values_list('id', 'coworkers__name')),
                ["(1, u'p2')", "(2, u'p1')", "(3, u'p1')", "(4, None)"]
            ),
        )
        for qset, expected in qsets:
            self.assertQuerysetEqual(qset, expected)
            self.assertEqual(qset.count(), len(expected))

        # Combining queries with different distinct_fields is not allowed.
        base_qs = Celebrity.objects.all()
        self.assertRaisesMessage(
            AssertionError,
            "Cannot combine queries with different distinct fields.",
            lambda: (base_qs.distinct('id') & base_qs.distinct('name'))
        )

        # Test join unreffing
        c1 = Celebrity.objects.distinct('greatest_fan__id', 'greatest_fan__fan_of')
        self.assertIn('OUTER JOIN', str(c1.query))
        c2 = c1.distinct('pk')
        self.assertNotIn('OUTER JOIN', str(c2.query))

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_distinct_not_implemented_checks(self):
        # distinct + annotate not allowed
        with self.assertRaises(NotImplementedError):
            Celebrity.objects.annotate(Max('id')).distinct('id')[0]
        with self.assertRaises(NotImplementedError):
            Celebrity.objects.distinct('id').annotate(Max('id'))[0]

        # However this check is done only when the query executes, so you
        # can use distinct() to remove the fields before execution.
        Celebrity.objects.distinct('id').annotate(Max('id')).distinct()[0]
        # distinct + aggregate not allowed
        with self.assertRaises(NotImplementedError):
            Celebrity.objects.distinct('id').aggregate(Max('id'))


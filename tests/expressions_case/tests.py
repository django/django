import unittest
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from operator import attrgetter, itemgetter
from uuid import UUID

from django.core.exceptions import FieldError
from django.db import connection, models
from django.db.models import F, Max, Min, Q, Sum, Value
from django.db.models.expressions import Case, When
from django.test import TestCase

from .models import CaseTestModel, Client, FKCaseTestModel, O2OCaseTestModel

try:
    from PIL import Image
except ImportError:
    Image = None


class CaseExpressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        o = CaseTestModel.objects.create(integer=1, integer2=1, string='1')
        O2OCaseTestModel.objects.create(o2o=o, integer=1)
        FKCaseTestModel.objects.create(fk=o, integer=1)

        o = CaseTestModel.objects.create(integer=2, integer2=3, string='2')
        O2OCaseTestModel.objects.create(o2o=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=3)

        o = CaseTestModel.objects.create(integer=3, integer2=4, string='3')
        O2OCaseTestModel.objects.create(o2o=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=4)

        o = CaseTestModel.objects.create(integer=2, integer2=2, string='2')
        O2OCaseTestModel.objects.create(o2o=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=3)

        o = CaseTestModel.objects.create(integer=3, integer2=4, string='3')
        O2OCaseTestModel.objects.create(o2o=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=4)

        o = CaseTestModel.objects.create(integer=3, integer2=3, string='3')
        O2OCaseTestModel.objects.create(o2o=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=4)

        o = CaseTestModel.objects.create(integer=4, integer2=5, string='4')
        O2OCaseTestModel.objects.create(o2o=o, integer=1)
        FKCaseTestModel.objects.create(fk=o, integer=5)

        # GROUP BY on Oracle fails with TextField/BinaryField; see #24096.
        cls.non_lob_fields = [
            f.name for f in CaseTestModel._meta.get_fields()
            if not (f.is_relation and f.auto_created) and not isinstance(f, (models.BinaryField, models.TextField))
        ]

    def test_annotate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(test=Case(
                When(integer=1, then=Value('one')),
                When(integer=2, then=Value('two')),
                default=Value('other'),
                output_field=models.CharField(),
            )).order_by('pk'),
            [(1, 'one'), (2, 'two'), (3, 'other'), (2, 'two'), (3, 'other'), (3, 'other'), (4, 'other')],
            transform=attrgetter('integer', 'test')
        )

    def test_annotate_without_default(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(test=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
                output_field=models.IntegerField(),
            )).order_by('pk'),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'test')
        )

    def test_annotate_with_expression_as_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(f_test=Case(
                When(integer=1, then=F('integer') + 1),
                When(integer=2, then=F('integer') + 3),
                default='integer',
            )).order_by('pk'),
            [(1, 2), (2, 5), (3, 3), (2, 5), (3, 3), (3, 3), (4, 4)],
            transform=attrgetter('integer', 'f_test')
        )

    def test_annotate_with_expression_as_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(f_test=Case(
                When(integer2=F('integer'), then=Value('equal')),
                When(integer2=F('integer') + 1, then=Value('+1')),
                output_field=models.CharField(),
            )).order_by('pk'),
            [(1, 'equal'), (2, '+1'), (3, '+1'), (2, 'equal'), (3, '+1'), (3, 'equal'), (4, '+1')],
            transform=attrgetter('integer', 'f_test')
        )

    def test_annotate_with_join_in_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(join_test=Case(
                When(integer=1, then=F('o2o_rel__integer') + 1),
                When(integer=2, then=F('o2o_rel__integer') + 3),
                default='o2o_rel__integer',
            )).order_by('pk'),
            [(1, 2), (2, 5), (3, 3), (2, 5), (3, 3), (3, 3), (4, 1)],
            transform=attrgetter('integer', 'join_test')
        )

    def test_annotate_with_in_clause(self):
        fk_rels = FKCaseTestModel.objects.filter(integer__in=[5])
        self.assertQuerysetEqual(
            CaseTestModel.objects.only('pk', 'integer').annotate(in_test=Sum(Case(
                When(fk_rel__in=fk_rels, then=F('fk_rel__integer')),
                default=Value(0),
            ))).order_by('pk'),
            [(1, 0), (2, 0), (3, 0), (2, 0), (3, 0), (3, 0), (4, 5)],
            transform=attrgetter('integer', 'in_test')
        )

    def test_annotate_with_join_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(join_test=Case(
                When(integer2=F('o2o_rel__integer'), then=Value('equal')),
                When(integer2=F('o2o_rel__integer') + 1, then=Value('+1')),
                default=Value('other'),
                output_field=models.CharField(),
            )).order_by('pk'),
            [(1, 'equal'), (2, '+1'), (3, '+1'), (2, 'equal'), (3, '+1'), (3, 'equal'), (4, 'other')],
            transform=attrgetter('integer', 'join_test')
        )

    def test_annotate_with_join_in_predicate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(join_test=Case(
                When(o2o_rel__integer=1, then=Value('one')),
                When(o2o_rel__integer=2, then=Value('two')),
                When(o2o_rel__integer=3, then=Value('three')),
                default=Value('other'),
                output_field=models.CharField(),
            )).order_by('pk'),
            [(1, 'one'), (2, 'two'), (3, 'three'), (2, 'two'), (3, 'three'), (3, 'three'), (4, 'one')],
            transform=attrgetter('integer', 'join_test')
        )

    def test_annotate_with_annotation_in_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F('integer') + 1,
                f_plus_3=F('integer') + 3,
            ).annotate(
                f_test=Case(
                    When(integer=1, then='f_plus_1'),
                    When(integer=2, then='f_plus_3'),
                    default='integer',
                ),
            ).order_by('pk'),
            [(1, 2), (2, 5), (3, 3), (2, 5), (3, 3), (3, 3), (4, 4)],
            transform=attrgetter('integer', 'f_test')
        )

    def test_annotate_with_annotation_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F('integer') + 1,
            ).annotate(
                f_test=Case(
                    When(integer2=F('integer'), then=Value('equal')),
                    When(integer2=F('f_plus_1'), then=Value('+1')),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [(1, 'equal'), (2, '+1'), (3, '+1'), (2, 'equal'), (3, '+1'), (3, 'equal'), (4, '+1')],
            transform=attrgetter('integer', 'f_test')
        )

    def test_annotate_with_annotation_in_predicate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                f_minus_2=F('integer') - 2,
            ).annotate(
                test=Case(
                    When(f_minus_2=-1, then=Value('negative one')),
                    When(f_minus_2=0, then=Value('zero')),
                    When(f_minus_2=1, then=Value('one')),
                    default=Value('other'),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [(1, 'negative one'), (2, 'zero'), (3, 'one'), (2, 'zero'), (3, 'one'), (3, 'one'), (4, 'other')],
            transform=attrgetter('integer', 'test')
        )

    def test_annotate_with_aggregation_in_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.values(*self.non_lob_fields).annotate(
                min=Min('fk_rel__integer'),
                max=Max('fk_rel__integer'),
            ).annotate(
                test=Case(
                    When(integer=2, then='min'),
                    When(integer=3, then='max'),
                ),
            ).order_by('pk'),
            [(1, None, 1, 1), (2, 2, 2, 3), (3, 4, 3, 4), (2, 2, 2, 3), (3, 4, 3, 4), (3, 4, 3, 4), (4, None, 5, 5)],
            transform=itemgetter('integer', 'test', 'min', 'max')
        )

    def test_annotate_with_aggregation_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.values(*self.non_lob_fields).annotate(
                min=Min('fk_rel__integer'),
                max=Max('fk_rel__integer'),
            ).annotate(
                test=Case(
                    When(integer2=F('min'), then=Value('min')),
                    When(integer2=F('max'), then=Value('max')),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [(1, 1, 'min'), (2, 3, 'max'), (3, 4, 'max'), (2, 2, 'min'), (3, 4, 'max'), (3, 3, 'min'), (4, 5, 'min')],
            transform=itemgetter('integer', 'integer2', 'test')
        )

    def test_annotate_with_aggregation_in_predicate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.values(*self.non_lob_fields).annotate(
                max=Max('fk_rel__integer'),
            ).annotate(
                test=Case(
                    When(max=3, then=Value('max = 3')),
                    When(max=4, then=Value('max = 4')),
                    default=Value(''),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [(1, 1, ''), (2, 3, 'max = 3'), (3, 4, 'max = 4'), (2, 3, 'max = 3'),
             (3, 4, 'max = 4'), (3, 4, 'max = 4'), (4, 5, '')],
            transform=itemgetter('integer', 'max', 'test')
        )

    def test_annotate_exclude(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(test=Case(
                When(integer=1, then=Value('one')),
                When(integer=2, then=Value('two')),
                default=Value('other'),
                output_field=models.CharField(),
            )).exclude(test='other').order_by('pk'),
            [(1, 'one'), (2, 'two'), (2, 'two')],
            transform=attrgetter('integer', 'test')
        )

    def test_annotate_values_not_in_order_by(self):
        self.assertEqual(
            list(CaseTestModel.objects.annotate(test=Case(
                When(integer=1, then=Value('one')),
                When(integer=2, then=Value('two')),
                When(integer=3, then=Value('three')),
                default=Value('other'),
                output_field=models.CharField(),
            )).order_by('test').values_list('integer', flat=True)),
            [1, 4, 3, 3, 3, 2, 2]
        )

    def test_annotate_with_empty_when(self):
        objects = CaseTestModel.objects.annotate(
            selected=Case(
                When(pk__in=[], then=Value('selected')),
                default=Value('not selected'), output_field=models.CharField()
            )
        )
        self.assertEqual(len(objects), CaseTestModel.objects.count())
        self.assertTrue(all(obj.selected == 'not selected' for obj in objects))

    def test_combined_expression(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=1, then=2),
                    When(integer=2, then=1),
                    default=3,
                    output_field=models.IntegerField(),
                ) + 1,
            ).order_by('pk'),
            [(1, 3), (2, 2), (3, 4), (2, 2), (3, 4), (3, 4), (4, 4)],
            transform=attrgetter('integer', 'test')
        )

    if connection.vendor == 'sqlite' and connection.Database.sqlite_version_info < (3, 7, 0):
        # There is a bug in sqlite < 3.7.0, where placeholder order is lost.
        # Thus, the above query returns  <condition_value> + <result_value>
        # for each matching case instead of <result_value> + 1 (#24148).
        test_combined_expression = unittest.expectedFailure(test_combined_expression)

    def test_in_subquery(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(
                pk__in=CaseTestModel.objects.annotate(
                    test=Case(
                        When(integer=F('integer2'), then='pk'),
                        When(integer=4, then='pk'),
                        output_field=models.IntegerField(),
                    ),
                ).values('test')).order_by('pk'),
            [(1, 1), (2, 2), (3, 3), (4, 5)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_case_reuse(self):
        SOME_CASE = Case(
            When(pk=0, then=Value('0')),
            default=Value('1'),
            output_field=models.CharField(),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(somecase=SOME_CASE).order_by('pk'),
            CaseTestModel.objects.annotate(somecase=SOME_CASE).order_by('pk').values_list('pk', 'somecase'),
            lambda x: (x.pk, x.somecase)
        )

    def test_aggregate(self):
        self.assertEqual(
            CaseTestModel.objects.aggregate(
                one=models.Sum(Case(
                    When(integer=1, then=1),
                    output_field=models.IntegerField(),
                )),
                two=models.Sum(Case(
                    When(integer=2, then=1),
                    output_field=models.IntegerField(),
                )),
                three=models.Sum(Case(
                    When(integer=3, then=1),
                    output_field=models.IntegerField(),
                )),
                four=models.Sum(Case(
                    When(integer=4, then=1),
                    output_field=models.IntegerField(),
                )),
            ),
            {'one': 1, 'two': 2, 'three': 3, 'four': 1}
        )

    def test_aggregate_with_expression_as_value(self):
        self.assertEqual(
            CaseTestModel.objects.aggregate(
                one=models.Sum(Case(When(integer=1, then='integer'))),
                two=models.Sum(Case(When(integer=2, then=F('integer') - 1))),
                three=models.Sum(Case(When(integer=3, then=F('integer') + 1))),
            ),
            {'one': 1, 'two': 2, 'three': 12}
        )

    def test_aggregate_with_expression_as_condition(self):
        self.assertEqual(
            CaseTestModel.objects.aggregate(
                equal=models.Sum(Case(
                    When(integer2=F('integer'), then=1),
                    output_field=models.IntegerField(),
                )),
                plus_one=models.Sum(Case(
                    When(integer2=F('integer') + 1, then=1),
                    output_field=models.IntegerField(),
                )),
            ),
            {'equal': 3, 'plus_one': 4}
        )

    def test_filter(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer2=Case(
                When(integer=2, then=3),
                When(integer=3, then=4),
                default=1,
                output_field=models.IntegerField(),
            )).order_by('pk'),
            [(1, 1), (2, 3), (3, 4), (3, 4)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_without_default(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer2=Case(
                When(integer=2, then=3),
                When(integer=3, then=4),
                output_field=models.IntegerField(),
            )).order_by('pk'),
            [(2, 3), (3, 4), (3, 4)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_expression_as_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer2=Case(
                When(integer=2, then=F('integer') + 1),
                When(integer=3, then=F('integer')),
                default='integer',
            )).order_by('pk'),
            [(1, 1), (2, 3), (3, 3)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_expression_as_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(string=Case(
                When(integer2=F('integer'), then=Value('2')),
                When(integer2=F('integer') + 1, then=Value('3')),
                output_field=models.CharField(),
            )).order_by('pk'),
            [(3, 4, '3'), (2, 2, '2'), (3, 4, '3')],
            transform=attrgetter('integer', 'integer2', 'string')
        )

    def test_filter_with_join_in_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer2=Case(
                When(integer=2, then=F('o2o_rel__integer') + 1),
                When(integer=3, then=F('o2o_rel__integer')),
                default='o2o_rel__integer',
            )).order_by('pk'),
            [(1, 1), (2, 3), (3, 3)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_join_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer=Case(
                When(integer2=F('o2o_rel__integer') + 1, then=2),
                When(integer2=F('o2o_rel__integer'), then=3),
                output_field=models.IntegerField(),
            )).order_by('pk'),
            [(2, 3), (3, 3)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_join_in_predicate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer2=Case(
                When(o2o_rel__integer=1, then=1),
                When(o2o_rel__integer=2, then=3),
                When(o2o_rel__integer=3, then=4),
                output_field=models.IntegerField(),
            )).order_by('pk'),
            [(1, 1), (2, 3), (3, 4), (3, 4)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_annotation_in_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                f=F('integer'),
                f_plus_1=F('integer') + 1,
            ).filter(
                integer2=Case(
                    When(integer=2, then='f_plus_1'),
                    When(integer=3, then='f'),
                ),
            ).order_by('pk'),
            [(2, 3), (3, 3)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_annotation_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F('integer') + 1,
            ).filter(
                integer=Case(
                    When(integer2=F('integer'), then=2),
                    When(integer2=F('f_plus_1'), then=3),
                    output_field=models.IntegerField(),
                ),
            ).order_by('pk'),
            [(3, 4), (2, 2), (3, 4)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_annotation_in_predicate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F('integer') + 1,
            ).filter(
                integer2=Case(
                    When(f_plus_1=3, then=3),
                    When(f_plus_1=4, then=4),
                    default=1,
                    output_field=models.IntegerField(),
                ),
            ).order_by('pk'),
            [(1, 1), (2, 3), (3, 4), (3, 4)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_filter_with_aggregation_in_value(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.values(*self.non_lob_fields).annotate(
                min=Min('fk_rel__integer'),
                max=Max('fk_rel__integer'),
            ).filter(
                integer2=Case(
                    When(integer=2, then='min'),
                    When(integer=3, then='max'),
                ),
            ).order_by('pk'),
            [(3, 4, 3, 4), (2, 2, 2, 3), (3, 4, 3, 4)],
            transform=itemgetter('integer', 'integer2', 'min', 'max')
        )

    def test_filter_with_aggregation_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.values(*self.non_lob_fields).annotate(
                min=Min('fk_rel__integer'),
                max=Max('fk_rel__integer'),
            ).filter(
                integer=Case(
                    When(integer2=F('min'), then=2),
                    When(integer2=F('max'), then=3),
                ),
            ).order_by('pk'),
            [(3, 4, 3, 4), (2, 2, 2, 3), (3, 4, 3, 4)],
            transform=itemgetter('integer', 'integer2', 'min', 'max')
        )

    def test_filter_with_aggregation_in_predicate(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.values(*self.non_lob_fields).annotate(
                max=Max('fk_rel__integer'),
            ).filter(
                integer=Case(
                    When(max=3, then=2),
                    When(max=4, then=3),
                ),
            ).order_by('pk'),
            [(2, 3, 3), (3, 4, 4), (2, 2, 3), (3, 4, 4), (3, 3, 4)],
            transform=itemgetter('integer', 'integer2', 'max')
        )

    def test_update(self):
        CaseTestModel.objects.update(
            string=Case(
                When(integer=1, then=Value('one')),
                When(integer=2, then=Value('two')),
                default=Value('other'),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 'one'), (2, 'two'), (3, 'other'), (2, 'two'), (3, 'other'), (3, 'other'), (4, 'other')],
            transform=attrgetter('integer', 'string')
        )

    def test_update_without_default(self):
        CaseTestModel.objects.update(
            integer2=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'integer2')
        )

    def test_update_with_expression_as_value(self):
        CaseTestModel.objects.update(
            integer=Case(
                When(integer=1, then=F('integer') + 1),
                When(integer=2, then=F('integer') + 3),
                default='integer',
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [('1', 2), ('2', 5), ('3', 3), ('2', 5), ('3', 3), ('3', 3), ('4', 4)],
            transform=attrgetter('string', 'integer')
        )

    def test_update_with_expression_as_condition(self):
        CaseTestModel.objects.update(
            string=Case(
                When(integer2=F('integer'), then=Value('equal')),
                When(integer2=F('integer') + 1, then=Value('+1')),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 'equal'), (2, '+1'), (3, '+1'), (2, 'equal'), (3, '+1'), (3, 'equal'), (4, '+1')],
            transform=attrgetter('integer', 'string')
        )

    def test_update_with_join_in_condition_raise_field_error(self):
        with self.assertRaisesMessage(FieldError, 'Joined field references are not permitted in this query'):
            CaseTestModel.objects.update(
                integer=Case(
                    When(integer2=F('o2o_rel__integer') + 1, then=2),
                    When(integer2=F('o2o_rel__integer'), then=3),
                    output_field=models.IntegerField(),
                ),
            )

    def test_update_with_join_in_predicate_raise_field_error(self):
        with self.assertRaisesMessage(FieldError, 'Joined field references are not permitted in this query'):
            CaseTestModel.objects.update(
                string=Case(
                    When(o2o_rel__integer=1, then=Value('one')),
                    When(o2o_rel__integer=2, then=Value('two')),
                    When(o2o_rel__integer=3, then=Value('three')),
                    default=Value('other'),
                    output_field=models.CharField(),
                ),
            )

    def test_update_big_integer(self):
        CaseTestModel.objects.update(
            big_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'big_integer')
        )

    def test_update_binary(self):
        CaseTestModel.objects.update(
            binary=Case(
                # fails on postgresql on Python 2.7 if output_field is not
                # set explicitly
                When(integer=1, then=Value(b'one', output_field=models.BinaryField())),
                When(integer=2, then=Value(b'two', output_field=models.BinaryField())),
                default=Value(b'', output_field=models.BinaryField()),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, b'one'), (2, b'two'), (3, b''), (2, b'two'), (3, b''), (3, b''), (4, b'')],
            transform=lambda o: (o.integer, bytes(o.binary))
        )

    def test_update_boolean(self):
        CaseTestModel.objects.update(
            boolean=Case(
                When(integer=1, then=True),
                When(integer=2, then=True),
                default=False,
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, True), (2, True), (3, False), (2, True), (3, False), (3, False), (4, False)],
            transform=attrgetter('integer', 'boolean')
        )

    def test_update_date(self):
        CaseTestModel.objects.update(
            date=Case(
                When(integer=1, then=date(2015, 1, 1)),
                When(integer=2, then=date(2015, 1, 2)),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [
                (1, date(2015, 1, 1)), (2, date(2015, 1, 2)), (3, None), (2, date(2015, 1, 2)),
                (3, None), (3, None), (4, None)
            ],
            transform=attrgetter('integer', 'date')
        )

    def test_update_date_time(self):
        CaseTestModel.objects.update(
            date_time=Case(
                When(integer=1, then=datetime(2015, 1, 1)),
                When(integer=2, then=datetime(2015, 1, 2)),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [
                (1, datetime(2015, 1, 1)), (2, datetime(2015, 1, 2)), (3, None), (2, datetime(2015, 1, 2)),
                (3, None), (3, None), (4, None)
            ],
            transform=attrgetter('integer', 'date_time')
        )

    def test_update_decimal(self):
        CaseTestModel.objects.update(
            decimal=Case(
                When(integer=1, then=Decimal('1.1')),
                When(integer=2, then=Decimal('2.2')),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [
                (1, Decimal('1.1')),
                (2, Decimal('2.2')),
                (3, None),
                (2, Decimal('2.2')),
                (3, None),
                (3, None),
                (4, None)
            ],
            transform=attrgetter('integer', 'decimal')
        )

    def test_update_duration(self):
        CaseTestModel.objects.update(
            duration=Case(
                # fails on sqlite if output_field is not set explicitly on all
                # Values containing timedeltas
                When(integer=1, then=Value(timedelta(1), output_field=models.DurationField())),
                When(integer=2, then=Value(timedelta(2), output_field=models.DurationField())),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, timedelta(1)), (2, timedelta(2)), (3, None), (2, timedelta(2)), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'duration')
        )

    def test_update_email(self):
        CaseTestModel.objects.update(
            email=Case(
                When(integer=1, then=Value('1@example.com')),
                When(integer=2, then=Value('2@example.com')),
                default=Value(''),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '1@example.com'), (2, '2@example.com'), (3, ''), (2, '2@example.com'), (3, ''), (3, ''), (4, '')],
            transform=attrgetter('integer', 'email')
        )

    def test_update_file(self):
        CaseTestModel.objects.update(
            file=Case(
                When(integer=1, then=Value('~/1')),
                When(integer=2, then=Value('~/2')),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '~/1'), (2, '~/2'), (3, ''), (2, '~/2'), (3, ''), (3, ''), (4, '')],
            transform=lambda o: (o.integer, str(o.file))
        )

    def test_update_file_path(self):
        CaseTestModel.objects.update(
            file_path=Case(
                When(integer=1, then=Value('~/1')),
                When(integer=2, then=Value('~/2')),
                default=Value(''),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '~/1'), (2, '~/2'), (3, ''), (2, '~/2'), (3, ''), (3, ''), (4, '')],
            transform=attrgetter('integer', 'file_path')
        )

    def test_update_float(self):
        CaseTestModel.objects.update(
            float=Case(
                When(integer=1, then=1.1),
                When(integer=2, then=2.2),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 1.1), (2, 2.2), (3, None), (2, 2.2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'float')
        )

    @unittest.skipUnless(Image, "Pillow not installed")
    def test_update_image(self):
        CaseTestModel.objects.update(
            image=Case(
                When(integer=1, then=Value('~/1')),
                When(integer=2, then=Value('~/2')),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '~/1'), (2, '~/2'), (3, ''), (2, '~/2'), (3, ''), (3, ''), (4, '')],
            transform=lambda o: (o.integer, str(o.image))
        )

    def test_update_generic_ip_address(self):
        CaseTestModel.objects.update(
            generic_ip_address=Case(
                # fails on postgresql if output_field is not set explicitly
                When(integer=1, then=Value('1.1.1.1')),
                When(integer=2, then=Value('2.2.2.2')),
                output_field=models.GenericIPAddressField(),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '1.1.1.1'), (2, '2.2.2.2'), (3, None), (2, '2.2.2.2'), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'generic_ip_address')
        )

    def test_update_null_boolean(self):
        CaseTestModel.objects.update(
            null_boolean=Case(
                When(integer=1, then=True),
                When(integer=2, then=False),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, True), (2, False), (3, None), (2, False), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'null_boolean')
        )

    def test_update_positive_integer(self):
        CaseTestModel.objects.update(
            positive_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'positive_integer')
        )

    def test_update_positive_small_integer(self):
        CaseTestModel.objects.update(
            positive_small_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'positive_small_integer')
        )

    def test_update_slug(self):
        CaseTestModel.objects.update(
            slug=Case(
                When(integer=1, then=Value('1')),
                When(integer=2, then=Value('2')),
                default=Value(''),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '1'), (2, '2'), (3, ''), (2, '2'), (3, ''), (3, ''), (4, '')],
            transform=attrgetter('integer', 'slug')
        )

    def test_update_small_integer(self):
        CaseTestModel.objects.update(
            small_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'small_integer')
        )

    def test_update_string(self):
        CaseTestModel.objects.filter(string__in=['1', '2']).update(
            string=Case(
                When(integer=1, then=Value('1', output_field=models.CharField())),
                When(integer=2, then=Value('2', output_field=models.CharField())),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(string__in=['1', '2']).order_by('pk'),
            [(1, '1'), (2, '2'), (2, '2')],
            transform=attrgetter('integer', 'string')
        )

    def test_update_text(self):
        CaseTestModel.objects.update(
            text=Case(
                When(integer=1, then=Value('1')),
                When(integer=2, then=Value('2')),
                default=Value(''),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, '1'), (2, '2'), (3, ''), (2, '2'), (3, ''), (3, ''), (4, '')],
            transform=attrgetter('integer', 'text')
        )

    def test_update_time(self):
        CaseTestModel.objects.update(
            time=Case(
                # fails on sqlite if output_field is not set explicitly on all
                # Values containing times
                When(integer=1, then=Value(time(1), output_field=models.TimeField())),
                When(integer=2, then=Value(time(2), output_field=models.TimeField())),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, time(1)), (2, time(2)), (3, None), (2, time(2)), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'time')
        )

    def test_update_url(self):
        CaseTestModel.objects.update(
            url=Case(
                When(integer=1, then=Value('http://1.example.com/')),
                When(integer=2, then=Value('http://2.example.com/')),
                default=Value(''),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [
                (1, 'http://1.example.com/'), (2, 'http://2.example.com/'), (3, ''), (2, 'http://2.example.com/'),
                (3, ''), (3, ''), (4, '')
            ],
            transform=attrgetter('integer', 'url')
        )

    def test_update_uuid(self):
        CaseTestModel.objects.update(
            uuid=Case(
                # fails on sqlite if output_field is not set explicitly on all
                # Values containing UUIDs
                When(integer=1, then=Value(
                    UUID('11111111111111111111111111111111'),
                    output_field=models.UUIDField(),
                )),
                When(integer=2, then=Value(
                    UUID('22222222222222222222222222222222'),
                    output_field=models.UUIDField(),
                )),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [
                (1, UUID('11111111111111111111111111111111')),
                (2, UUID('22222222222222222222222222222222')),
                (3, None),
                (2, UUID('22222222222222222222222222222222')),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter('integer', 'uuid')
        )

    def test_update_fk(self):
        obj1, obj2 = CaseTestModel.objects.all()[:2]

        CaseTestModel.objects.update(
            fk=Case(
                When(integer=1, then=obj1.pk),
                When(integer=2, then=obj2.pk),
            ),
        )
        self.assertQuerysetEqual(
            CaseTestModel.objects.all().order_by('pk'),
            [(1, obj1.pk), (2, obj2.pk), (3, None), (2, obj2.pk), (3, None), (3, None), (4, None)],
            transform=attrgetter('integer', 'fk_id')
        )

    def test_lookup_in_condition(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer__lt=2, then=Value('less than 2')),
                    When(integer__gt=2, then=Value('greater than 2')),
                    default=Value('equal to 2'),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [
                (1, 'less than 2'), (2, 'equal to 2'), (3, 'greater than 2'), (2, 'equal to 2'), (3, 'greater than 2'),
                (3, 'greater than 2'), (4, 'greater than 2')
            ],
            transform=attrgetter('integer', 'test')
        )

    def test_lookup_different_fields(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=2, integer2=3, then=Value('when')),
                    default=Value('default'),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [
                (1, 1, 'default'), (2, 3, 'when'), (3, 4, 'default'), (2, 2, 'default'), (3, 4, 'default'),
                (3, 3, 'default'), (4, 5, 'default')
            ],
            transform=attrgetter('integer', 'integer2', 'test')
        )

    def test_combined_q_object(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(Q(integer=2) | Q(integer2=3), then=Value('when')),
                    default=Value('default'),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [
                (1, 1, 'default'), (2, 3, 'when'), (3, 4, 'default'), (2, 2, 'when'), (3, 4, 'default'),
                (3, 3, 'when'), (4, 5, 'default')
            ],
            transform=attrgetter('integer', 'integer2', 'test')
        )

    def test_order_by_conditional_implicit(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer__lte=2).annotate(test=Case(
                When(integer=1, then=2),
                When(integer=2, then=1),
                default=3,
                output_field=models.IntegerField(),
            )).order_by('test', 'pk'),
            [(2, 1), (2, 1), (1, 2)],
            transform=attrgetter('integer', 'test')
        )

    def test_order_by_conditional_explicit(self):
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(integer__lte=2).annotate(test=Case(
                When(integer=1, then=2),
                When(integer=2, then=1),
                default=3,
                output_field=models.IntegerField(),
            )).order_by(F('test').asc(), 'pk'),
            [(2, 1), (2, 1), (1, 2)],
            transform=attrgetter('integer', 'test')
        )

    def test_join_promotion(self):
        o = CaseTestModel.objects.create(integer=1, integer2=1, string='1')
        # Testing that:
        # 1. There isn't any object on the remote side of the fk_rel
        #    relation. If the query used inner joins, then the join to fk_rel
        #    would remove o from the results. So, in effect we are testing that
        #    we are promoting the fk_rel join to a left outer join here.
        # 2. The default value of 3 is generated for the case expression.
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__pk=1, then=2),
                    default=3,
                    output_field=models.IntegerField()
                ),
            ),
            [(o, 3)],
            lambda x: (x, x.foo)
        )
        # Now 2 should be generated, as the fk_rel is null.
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__isnull=True, then=2),
                    default=3,
                    output_field=models.IntegerField()
                ),
            ),
            [(o, 2)],
            lambda x: (x, x.foo)
        )

    def test_join_promotion_multiple_annotations(self):
        o = CaseTestModel.objects.create(integer=1, integer2=1, string='1')
        # Testing that:
        # 1. There isn't any object on the remote side of the fk_rel
        #    relation. If the query used inner joins, then the join to fk_rel
        #    would remove o from the results. So, in effect we are testing that
        #    we are promoting the fk_rel join to a left outer join here.
        # 2. The default value of 3 is generated for the case expression.
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__pk=1, then=2),
                    default=3,
                    output_field=models.IntegerField()
                ),
                bar=Case(
                    When(fk_rel__pk=1, then=4),
                    default=5,
                    output_field=models.IntegerField()
                ),
            ),
            [(o, 3, 5)],
            lambda x: (x, x.foo, x.bar)
        )
        # Now 2 should be generated, as the fk_rel is null.
        self.assertQuerysetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__isnull=True, then=2),
                    default=3,
                    output_field=models.IntegerField()
                ),
                bar=Case(
                    When(fk_rel__isnull=True, then=4),
                    default=5,
                    output_field=models.IntegerField()
                ),
            ),
            [(o, 2, 4)],
            lambda x: (x, x.foo, x.bar)
        )

    def test_m2m_exclude(self):
        CaseTestModel.objects.create(integer=10, integer2=1, string='1')
        qs = CaseTestModel.objects.values_list('id', 'integer').annotate(
            cnt=models.Sum(
                Case(When(~Q(fk_rel__integer=1), then=1), default=2),
                output_field=models.IntegerField()
            ),
        ).order_by('integer')
        # The first o has 2 as its fk_rel__integer=1, thus it hits the
        # default=2 case. The other ones have 2 as the result as they have 2
        # fk_rel objects, except for integer=4 and integer=10 (created above).
        # The integer=4 case has one integer, thus the result is 1, and
        # integer=10 doesn't have any and this too generates 1 (instead of 0)
        # as ~Q() also matches nulls.
        self.assertQuerysetEqual(
            qs,
            [(1, 2), (2, 2), (2, 2), (3, 2), (3, 2), (3, 2), (4, 1), (10, 1)],
            lambda x: x[1:]
        )

    def test_m2m_reuse(self):
        CaseTestModel.objects.create(integer=10, integer2=1, string='1')
        # Need to use values before annotate so that Oracle will not group
        # by fields it isn't capable of grouping by.
        qs = CaseTestModel.objects.values_list('id', 'integer').annotate(
            cnt=models.Sum(
                Case(When(~Q(fk_rel__integer=1), then=1), default=2),
                output_field=models.IntegerField()
            ),
        ).annotate(
            cnt2=models.Sum(
                Case(When(~Q(fk_rel__integer=1), then=1), default=2),
                output_field=models.IntegerField()
            ),
        ).order_by('integer')
        self.assertEqual(str(qs.query).count(' JOIN '), 1)
        self.assertQuerysetEqual(
            qs,
            [(1, 2, 2), (2, 2, 2), (2, 2, 2), (3, 2, 2), (3, 2, 2), (3, 2, 2), (4, 1, 1), (10, 1, 1)],
            lambda x: x[1:]
        )


class CaseDocumentationExamples(TestCase):
    @classmethod
    def setUpTestData(cls):
        Client.objects.create(
            name='Jane Doe',
            account_type=Client.REGULAR,
            registered_on=date.today() - timedelta(days=36),
        )
        Client.objects.create(
            name='James Smith',
            account_type=Client.GOLD,
            registered_on=date.today() - timedelta(days=5),
        )
        Client.objects.create(
            name='Jack Black',
            account_type=Client.PLATINUM,
            registered_on=date.today() - timedelta(days=10 * 365),
        )

    def test_simple_example(self):
        self.assertQuerysetEqual(
            Client.objects.annotate(
                discount=Case(
                    When(account_type=Client.GOLD, then=Value('5%')),
                    When(account_type=Client.PLATINUM, then=Value('10%')),
                    default=Value('0%'),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [('Jane Doe', '0%'), ('James Smith', '5%'), ('Jack Black', '10%')],
            transform=attrgetter('name', 'discount')
        )

    def test_lookup_example(self):
        a_month_ago = date.today() - timedelta(days=30)
        a_year_ago = date.today() - timedelta(days=365)
        self.assertQuerysetEqual(
            Client.objects.annotate(
                discount=Case(
                    When(registered_on__lte=a_year_ago, then=Value('10%')),
                    When(registered_on__lte=a_month_ago, then=Value('5%')),
                    default=Value('0%'),
                    output_field=models.CharField(),
                ),
            ).order_by('pk'),
            [('Jane Doe', '5%'), ('James Smith', '0%'), ('Jack Black', '10%')],
            transform=attrgetter('name', 'discount')
        )

    def test_conditional_update_example(self):
        a_month_ago = date.today() - timedelta(days=30)
        a_year_ago = date.today() - timedelta(days=365)
        Client.objects.update(
            account_type=Case(
                When(registered_on__lte=a_year_ago, then=Value(Client.PLATINUM)),
                When(registered_on__lte=a_month_ago, then=Value(Client.GOLD)),
                default=Value(Client.REGULAR),
            ),
        )
        self.assertQuerysetEqual(
            Client.objects.all().order_by('pk'),
            [('Jane Doe', 'G'), ('James Smith', 'R'), ('Jack Black', 'P')],
            transform=attrgetter('name', 'account_type')
        )

    def test_conditional_aggregation_example(self):
        Client.objects.create(
            name='Jean Grey',
            account_type=Client.REGULAR,
            registered_on=date.today(),
        )
        Client.objects.create(
            name='James Bond',
            account_type=Client.PLATINUM,
            registered_on=date.today(),
        )
        Client.objects.create(
            name='Jane Porter',
            account_type=Client.PLATINUM,
            registered_on=date.today(),
        )
        self.assertEqual(
            Client.objects.aggregate(
                regular=models.Sum(Case(
                    When(account_type=Client.REGULAR, then=1),
                    output_field=models.IntegerField(),
                )),
                gold=models.Sum(Case(
                    When(account_type=Client.GOLD, then=1),
                    output_field=models.IntegerField(),
                )),
                platinum=models.Sum(Case(
                    When(account_type=Client.PLATINUM, then=1),
                    output_field=models.IntegerField(),
                )),
            ),
            {'regular': 2, 'gold': 1, 'platinum': 3}
        )

    def test_filter_example(self):
        a_month_ago = date.today() - timedelta(days=30)
        a_year_ago = date.today() - timedelta(days=365)
        self.assertQuerysetEqual(
            Client.objects.filter(
                registered_on__lte=Case(
                    When(account_type=Client.GOLD, then=a_month_ago),
                    When(account_type=Client.PLATINUM, then=a_year_ago),
                ),
            ),
            [('Jack Black', 'P')],
            transform=attrgetter('name', 'account_type')
        )

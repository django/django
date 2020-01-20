import json

from django.db.models import CharField, Q
from django.db.models.expressions import F, OuterRef, Subquery, Value
from django.db.models.functions import Cast, Concat, Substr
from django.test.utils import Approximate

from . import PostgreSQLTestCase
from .models import AggregateTestModel, StatTestModel

try:
    from django.contrib.postgres.aggregates import (
        ArrayAgg, BitAnd, BitOr, BoolAnd, BoolOr, Corr, CovarPop, JSONBAgg,
        RegrAvgX, RegrAvgY, RegrCount, RegrIntercept, RegrR2, RegrSlope,
        RegrSXX, RegrSXY, RegrSYY, StatAggregate, StringAgg,
    )
except ImportError:
    pass  # psycopg2 is not installed


class TestGeneralAggregate(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.agg1 = AggregateTestModel.objects.create(boolean_field=True, char_field='Foo1', integer_field=0)
        AggregateTestModel.objects.create(boolean_field=False, char_field='Foo2', integer_field=1)
        AggregateTestModel.objects.create(boolean_field=False, char_field='Foo4', integer_field=2)
        AggregateTestModel.objects.create(boolean_field=True, char_field='Foo3', integer_field=0)

    def test_array_agg_charfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('char_field'))
        self.assertEqual(values, {'arrayagg': ['Foo1', 'Foo2', 'Foo4', 'Foo3']})

    def test_array_agg_charfield_ordering(self):
        ordering_test_cases = (
            (F('char_field').desc(), ['Foo4', 'Foo3', 'Foo2', 'Foo1']),
            (F('char_field').asc(), ['Foo1', 'Foo2', 'Foo3', 'Foo4']),
            (F('char_field'), ['Foo1', 'Foo2', 'Foo3', 'Foo4']),
            ([F('boolean_field'), F('char_field').desc()], ['Foo4', 'Foo2', 'Foo3', 'Foo1']),
            ((F('boolean_field'), F('char_field').desc()), ['Foo4', 'Foo2', 'Foo3', 'Foo1']),
            ('char_field', ['Foo1', 'Foo2', 'Foo3', 'Foo4']),
            ('-char_field', ['Foo4', 'Foo3', 'Foo2', 'Foo1']),
            (Concat('char_field', Value('@')), ['Foo1', 'Foo2', 'Foo3', 'Foo4']),
            (Concat('char_field', Value('@')).desc(), ['Foo4', 'Foo3', 'Foo2', 'Foo1']),
            (
                (Substr('char_field', 1, 1), F('integer_field'), Substr('char_field', 4, 1).desc()),
                ['Foo3', 'Foo1', 'Foo2', 'Foo4'],
            ),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    arrayagg=ArrayAgg('char_field', ordering=ordering)
                )
                self.assertEqual(values, {'arrayagg': expected_output})

    def test_array_agg_integerfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('integer_field'))
        self.assertEqual(values, {'arrayagg': [0, 1, 2, 0]})

    def test_array_agg_integerfield_ordering(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg('integer_field', ordering=F('integer_field').desc())
        )
        self.assertEqual(values, {'arrayagg': [2, 1, 0, 0]})

    def test_array_agg_booleanfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('boolean_field'))
        self.assertEqual(values, {'arrayagg': [True, False, False, True]})

    def test_array_agg_booleanfield_ordering(self):
        ordering_test_cases = (
            (F('boolean_field').asc(), [False, False, True, True]),
            (F('boolean_field').desc(), [True, True, False, False]),
            (F('boolean_field'), [False, False, True, True]),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    arrayagg=ArrayAgg('boolean_field', ordering=ordering)
                )
                self.assertEqual(values, {'arrayagg': expected_output})

    def test_array_agg_filter(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg('integer_field', filter=Q(integer_field__gt=0)),
        )
        self.assertEqual(values, {'arrayagg': [1, 2]})

    def test_array_agg_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('char_field'))
        self.assertEqual(values, {'arrayagg': []})
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('integer_field'))
        self.assertEqual(values, {'arrayagg': []})
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('boolean_field'))
        self.assertEqual(values, {'arrayagg': []})

    def test_array_agg_lookups(self):
        aggr1 = AggregateTestModel.objects.create()
        aggr2 = AggregateTestModel.objects.create()
        StatTestModel.objects.create(related_field=aggr1, int1=1, int2=0)
        StatTestModel.objects.create(related_field=aggr1, int1=2, int2=0)
        StatTestModel.objects.create(related_field=aggr2, int1=3, int2=0)
        StatTestModel.objects.create(related_field=aggr2, int1=4, int2=0)
        qs = StatTestModel.objects.values('related_field').annotate(
            array=ArrayAgg('int1')
        ).filter(array__overlap=[2]).values_list('array', flat=True)
        self.assertCountEqual(qs.get(), [1, 2])

    def test_bit_and_general(self):
        values = AggregateTestModel.objects.filter(
            integer_field__in=[0, 1]).aggregate(bitand=BitAnd('integer_field'))
        self.assertEqual(values, {'bitand': 0})

    def test_bit_and_on_only_true_values(self):
        values = AggregateTestModel.objects.filter(
            integer_field=1).aggregate(bitand=BitAnd('integer_field'))
        self.assertEqual(values, {'bitand': 1})

    def test_bit_and_on_only_false_values(self):
        values = AggregateTestModel.objects.filter(
            integer_field=0).aggregate(bitand=BitAnd('integer_field'))
        self.assertEqual(values, {'bitand': 0})

    def test_bit_and_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(bitand=BitAnd('integer_field'))
        self.assertEqual(values, {'bitand': None})

    def test_bit_or_general(self):
        values = AggregateTestModel.objects.filter(
            integer_field__in=[0, 1]).aggregate(bitor=BitOr('integer_field'))
        self.assertEqual(values, {'bitor': 1})

    def test_bit_or_on_only_true_values(self):
        values = AggregateTestModel.objects.filter(
            integer_field=1).aggregate(bitor=BitOr('integer_field'))
        self.assertEqual(values, {'bitor': 1})

    def test_bit_or_on_only_false_values(self):
        values = AggregateTestModel.objects.filter(
            integer_field=0).aggregate(bitor=BitOr('integer_field'))
        self.assertEqual(values, {'bitor': 0})

    def test_bit_or_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(bitor=BitOr('integer_field'))
        self.assertEqual(values, {'bitor': None})

    def test_bool_and_general(self):
        values = AggregateTestModel.objects.aggregate(booland=BoolAnd('boolean_field'))
        self.assertEqual(values, {'booland': False})

    def test_bool_and_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(booland=BoolAnd('boolean_field'))
        self.assertEqual(values, {'booland': None})

    def test_bool_or_general(self):
        values = AggregateTestModel.objects.aggregate(boolor=BoolOr('boolean_field'))
        self.assertEqual(values, {'boolor': True})

    def test_bool_or_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(boolor=BoolOr('boolean_field'))
        self.assertEqual(values, {'boolor': None})

    def test_string_agg_requires_delimiter(self):
        with self.assertRaises(TypeError):
            AggregateTestModel.objects.aggregate(stringagg=StringAgg('char_field'))

    def test_string_agg_charfield(self):
        values = AggregateTestModel.objects.aggregate(stringagg=StringAgg('char_field', delimiter=';'))
        self.assertEqual(values, {'stringagg': 'Foo1;Foo2;Foo4;Foo3'})

    def test_string_agg_charfield_ordering(self):
        ordering_test_cases = (
            (F('char_field').desc(), 'Foo4;Foo3;Foo2;Foo1'),
            (F('char_field').asc(), 'Foo1;Foo2;Foo3;Foo4'),
            (F('char_field'), 'Foo1;Foo2;Foo3;Foo4'),
            ('char_field', 'Foo1;Foo2;Foo3;Foo4'),
            ('-char_field', 'Foo4;Foo3;Foo2;Foo1'),
            (Concat('char_field', Value('@')), 'Foo1;Foo2;Foo3;Foo4'),
            (Concat('char_field', Value('@')).desc(), 'Foo4;Foo3;Foo2;Foo1'),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    stringagg=StringAgg('char_field', delimiter=';', ordering=ordering)
                )
                self.assertEqual(values, {'stringagg': expected_output})

    def test_string_agg_filter(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg(
                'char_field',
                delimiter=';',
                filter=Q(char_field__endswith='3') | Q(char_field__endswith='1'),
            )
        )
        self.assertEqual(values, {'stringagg': 'Foo1;Foo3'})

    def test_string_agg_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(stringagg=StringAgg('char_field', delimiter=';'))
        self.assertEqual(values, {'stringagg': ''})

    def test_orderable_agg_alternative_fields(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg('integer_field', ordering=F('char_field').asc())
        )
        self.assertEqual(values, {'arrayagg': [0, 1, 0, 2]})

    def test_json_agg(self):
        values = AggregateTestModel.objects.aggregate(jsonagg=JSONBAgg('char_field'))
        self.assertEqual(values, {'jsonagg': ['Foo1', 'Foo2', 'Foo4', 'Foo3']})

    def test_json_agg_empty(self):
        values = AggregateTestModel.objects.none().aggregate(jsonagg=JSONBAgg('integer_field'))
        self.assertEqual(values, json.loads('{"jsonagg": []}'))

    def test_string_agg_array_agg_ordering_in_subquery(self):
        stats = []
        for i, agg in enumerate(AggregateTestModel.objects.order_by('char_field')):
            stats.append(StatTestModel(related_field=agg, int1=i, int2=i + 1))
            stats.append(StatTestModel(related_field=agg, int1=i + 1, int2=i))
        StatTestModel.objects.bulk_create(stats)

        for aggregate, expected_result in (
            (
                ArrayAgg('stattestmodel__int1', ordering='-stattestmodel__int2'),
                [('Foo1', [0, 1]), ('Foo2', [1, 2]), ('Foo3', [2, 3]), ('Foo4', [3, 4])],
            ),
            (
                StringAgg(
                    Cast('stattestmodel__int1', CharField()),
                    delimiter=';',
                    ordering='-stattestmodel__int2',
                ),
                [('Foo1', '0;1'), ('Foo2', '1;2'), ('Foo3', '2;3'), ('Foo4', '3;4')],
            ),
        ):
            with self.subTest(aggregate=aggregate.__class__.__name__):
                subquery = AggregateTestModel.objects.filter(
                    pk=OuterRef('pk'),
                ).annotate(agg=aggregate).values('agg')
                values = AggregateTestModel.objects.annotate(
                    agg=Subquery(subquery),
                ).order_by('char_field').values_list('char_field', 'agg')
                self.assertEqual(list(values), expected_result)

    def test_string_agg_array_agg_filter_in_subquery(self):
        StatTestModel.objects.bulk_create([
            StatTestModel(related_field=self.agg1, int1=0, int2=5),
            StatTestModel(related_field=self.agg1, int1=1, int2=4),
            StatTestModel(related_field=self.agg1, int1=2, int2=3),
        ])
        for aggregate, expected_result in (
            (
                ArrayAgg('stattestmodel__int1', filter=Q(stattestmodel__int2__gt=3)),
                [('Foo1', [0, 1]), ('Foo2', None)],
            ),
            (
                StringAgg(
                    Cast('stattestmodel__int2', CharField()),
                    delimiter=';',
                    filter=Q(stattestmodel__int1__lt=2),
                ),
                [('Foo1', '5;4'), ('Foo2', None)],
            ),
        ):
            with self.subTest(aggregate=aggregate.__class__.__name__):
                subquery = AggregateTestModel.objects.filter(
                    pk=OuterRef('pk'),
                ).annotate(agg=aggregate).values('agg')
                values = AggregateTestModel.objects.annotate(
                    agg=Subquery(subquery),
                ).filter(
                    char_field__in=['Foo1', 'Foo2'],
                ).order_by('char_field').values_list('char_field', 'agg')
                self.assertEqual(list(values), expected_result)

    def test_string_agg_filter_in_subquery_with_exclude(self):
        subquery = AggregateTestModel.objects.annotate(
            stringagg=StringAgg(
                'char_field',
                delimiter=';',
                filter=Q(char_field__endswith='1'),
            )
        ).exclude(stringagg='').values('id')
        self.assertSequenceEqual(
            AggregateTestModel.objects.filter(id__in=Subquery(subquery)),
            [self.agg1],
        )


class TestAggregateDistinct(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        AggregateTestModel.objects.create(char_field='Foo')
        AggregateTestModel.objects.create(char_field='Foo')
        AggregateTestModel.objects.create(char_field='Bar')

    def test_string_agg_distinct_false(self):
        values = AggregateTestModel.objects.aggregate(stringagg=StringAgg('char_field', delimiter=' ', distinct=False))
        self.assertEqual(values['stringagg'].count('Foo'), 2)
        self.assertEqual(values['stringagg'].count('Bar'), 1)

    def test_string_agg_distinct_true(self):
        values = AggregateTestModel.objects.aggregate(stringagg=StringAgg('char_field', delimiter=' ', distinct=True))
        self.assertEqual(values['stringagg'].count('Foo'), 1)
        self.assertEqual(values['stringagg'].count('Bar'), 1)

    def test_array_agg_distinct_false(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('char_field', distinct=False))
        self.assertEqual(sorted(values['arrayagg']), ['Bar', 'Foo', 'Foo'])

    def test_array_agg_distinct_true(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('char_field', distinct=True))
        self.assertEqual(sorted(values['arrayagg']), ['Bar', 'Foo'])


class TestStatisticsAggregate(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        StatTestModel.objects.create(
            int1=1,
            int2=3,
            related_field=AggregateTestModel.objects.create(integer_field=0),
        )
        StatTestModel.objects.create(
            int1=2,
            int2=2,
            related_field=AggregateTestModel.objects.create(integer_field=1),
        )
        StatTestModel.objects.create(
            int1=3,
            int2=1,
            related_field=AggregateTestModel.objects.create(integer_field=2),
        )

    # Tests for base class (StatAggregate)

    def test_missing_arguments_raises_exception(self):
        with self.assertRaisesMessage(ValueError, 'Both y and x must be provided.'):
            StatAggregate(x=None, y=None)

    def test_correct_source_expressions(self):
        func = StatAggregate(x='test', y=13)
        self.assertIsInstance(func.source_expressions[0], Value)
        self.assertIsInstance(func.source_expressions[1], F)

    def test_alias_is_required(self):
        class SomeFunc(StatAggregate):
            function = 'TEST'
        with self.assertRaisesMessage(TypeError, 'Complex aggregates require an alias'):
            StatTestModel.objects.aggregate(SomeFunc(y='int2', x='int1'))

    # Test aggregates

    def test_corr_general(self):
        values = StatTestModel.objects.aggregate(corr=Corr(y='int2', x='int1'))
        self.assertEqual(values, {'corr': -1.0})

    def test_corr_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(corr=Corr(y='int2', x='int1'))
        self.assertEqual(values, {'corr': None})

    def test_covar_pop_general(self):
        values = StatTestModel.objects.aggregate(covarpop=CovarPop(y='int2', x='int1'))
        self.assertEqual(values, {'covarpop': Approximate(-0.66, places=1)})

    def test_covar_pop_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(covarpop=CovarPop(y='int2', x='int1'))
        self.assertEqual(values, {'covarpop': None})

    def test_covar_pop_sample(self):
        values = StatTestModel.objects.aggregate(covarpop=CovarPop(y='int2', x='int1', sample=True))
        self.assertEqual(values, {'covarpop': -1.0})

    def test_covar_pop_sample_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(covarpop=CovarPop(y='int2', x='int1', sample=True))
        self.assertEqual(values, {'covarpop': None})

    def test_regr_avgx_general(self):
        values = StatTestModel.objects.aggregate(regravgx=RegrAvgX(y='int2', x='int1'))
        self.assertEqual(values, {'regravgx': 2.0})

    def test_regr_avgx_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regravgx=RegrAvgX(y='int2', x='int1'))
        self.assertEqual(values, {'regravgx': None})

    def test_regr_avgy_general(self):
        values = StatTestModel.objects.aggregate(regravgy=RegrAvgY(y='int2', x='int1'))
        self.assertEqual(values, {'regravgy': 2.0})

    def test_regr_avgy_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regravgy=RegrAvgY(y='int2', x='int1'))
        self.assertEqual(values, {'regravgy': None})

    def test_regr_count_general(self):
        values = StatTestModel.objects.aggregate(regrcount=RegrCount(y='int2', x='int1'))
        self.assertEqual(values, {'regrcount': 3})

    def test_regr_count_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrcount=RegrCount(y='int2', x='int1'))
        self.assertEqual(values, {'regrcount': 0})

    def test_regr_intercept_general(self):
        values = StatTestModel.objects.aggregate(regrintercept=RegrIntercept(y='int2', x='int1'))
        self.assertEqual(values, {'regrintercept': 4})

    def test_regr_intercept_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrintercept=RegrIntercept(y='int2', x='int1'))
        self.assertEqual(values, {'regrintercept': None})

    def test_regr_r2_general(self):
        values = StatTestModel.objects.aggregate(regrr2=RegrR2(y='int2', x='int1'))
        self.assertEqual(values, {'regrr2': 1})

    def test_regr_r2_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrr2=RegrR2(y='int2', x='int1'))
        self.assertEqual(values, {'regrr2': None})

    def test_regr_slope_general(self):
        values = StatTestModel.objects.aggregate(regrslope=RegrSlope(y='int2', x='int1'))
        self.assertEqual(values, {'regrslope': -1})

    def test_regr_slope_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrslope=RegrSlope(y='int2', x='int1'))
        self.assertEqual(values, {'regrslope': None})

    def test_regr_sxx_general(self):
        values = StatTestModel.objects.aggregate(regrsxx=RegrSXX(y='int2', x='int1'))
        self.assertEqual(values, {'regrsxx': 2.0})

    def test_regr_sxx_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrsxx=RegrSXX(y='int2', x='int1'))
        self.assertEqual(values, {'regrsxx': None})

    def test_regr_sxy_general(self):
        values = StatTestModel.objects.aggregate(regrsxy=RegrSXY(y='int2', x='int1'))
        self.assertEqual(values, {'regrsxy': -2.0})

    def test_regr_sxy_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrsxy=RegrSXY(y='int2', x='int1'))
        self.assertEqual(values, {'regrsxy': None})

    def test_regr_syy_general(self):
        values = StatTestModel.objects.aggregate(regrsyy=RegrSYY(y='int2', x='int1'))
        self.assertEqual(values, {'regrsyy': 2.0})

    def test_regr_syy_empty_result(self):
        StatTestModel.objects.all().delete()
        values = StatTestModel.objects.aggregate(regrsyy=RegrSYY(y='int2', x='int1'))
        self.assertEqual(values, {'regrsyy': None})

    def test_regr_avgx_with_related_obj_and_number_as_argument(self):
        """
        This is more complex test to check if JOIN on field and
        number as argument works as expected.
        """
        values = StatTestModel.objects.aggregate(complex_regravgx=RegrAvgX(y=5, x='related_field__integer_field'))
        self.assertEqual(values, {'complex_regravgx': 1.0})

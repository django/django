import json

from django.db.models.expressions import F, Value
from django.test.testcases import skipUnlessDBFeature
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
        AggregateTestModel.objects.create(boolean_field=True, char_field='Foo1', integer_field=0)
        AggregateTestModel.objects.create(boolean_field=False, char_field='Foo2', integer_field=1)
        AggregateTestModel.objects.create(boolean_field=False, char_field='Foo3', integer_field=2)
        AggregateTestModel.objects.create(boolean_field=True, char_field='Foo4', integer_field=0)

    def test_array_agg_charfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('char_field'))
        self.assertEqual(values, {'arrayagg': ['Foo1', 'Foo2', 'Foo3', 'Foo4']})

    def test_array_agg_integerfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('integer_field'))
        self.assertEqual(values, {'arrayagg': [0, 1, 2, 0]})

    def test_array_agg_booleanfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('boolean_field'))
        self.assertEqual(values, {'arrayagg': [True, False, False, True]})

    def test_array_agg_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('char_field'))
        self.assertEqual(values, {'arrayagg': []})
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('integer_field'))
        self.assertEqual(values, {'arrayagg': []})
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg('boolean_field'))
        self.assertEqual(values, {'arrayagg': []})

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
        self.assertEqual(values, {'stringagg': 'Foo1;Foo2;Foo3;Foo4'})

    def test_string_agg_empty_result(self):
        AggregateTestModel.objects.all().delete()
        values = AggregateTestModel.objects.aggregate(stringagg=StringAgg('char_field', delimiter=';'))
        self.assertEqual(values, {'stringagg': ''})

    @skipUnlessDBFeature('has_jsonb_agg')
    def test_json_agg(self):
        values = AggregateTestModel.objects.aggregate(jsonagg=JSONBAgg('char_field'))
        self.assertEqual(values, {'jsonagg': ['Foo1', 'Foo2', 'Foo3', 'Foo4']})

    @skipUnlessDBFeature('has_jsonb_agg')
    def test_json_agg_empty(self):
        values = AggregateTestModel.objects.none().aggregate(jsonagg=JSONBAgg('integer_field'))
        self.assertEqual(values, json.loads('{"jsonagg": []}'))


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

import contextlib
import time
import unittest
from datetime import date, datetime

from django.core.exceptions import FieldError
from django.db import connection, models
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Article, Author, MySQLUnixTimestamp


@contextlib.contextmanager
def register_lookup(field, *lookups):
    try:
        for lookup in lookups:
            field.register_lookup(lookup)
        yield
    finally:
        for lookup in lookups:
            field._unregister_lookup(lookup)


class Div3Lookup(models.Lookup):
    lookup_name = 'div3'

    def as_sql(self, compiler, connection):
        lhs, params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        return '(%s) %%%% 3 = %s' % (lhs, rhs), params

    def as_oracle(self, compiler, connection):
        lhs, params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        return 'mod(%s, 3) = %s' % (lhs, rhs), params


class Div3Transform(models.Transform):
    lookup_name = 'div3'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = compiler.compile(self.lhs)
        return '(%s) %%%% 3' % lhs, lhs_params

    def as_oracle(self, compiler, connection):
        lhs, lhs_params = compiler.compile(self.lhs)
        return 'mod(%s, 3)' % lhs, lhs_params


class Div3BilateralTransform(Div3Transform):
    bilateral = True


class Mult3BilateralTransform(models.Transform):
    bilateral = True
    lookup_name = 'mult3'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = compiler.compile(self.lhs)
        return '3 * (%s)' % lhs, lhs_params


class UpperBilateralTransform(models.Transform):
    bilateral = True
    lookup_name = 'upper'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = compiler.compile(self.lhs)
        return 'UPPER(%s)' % lhs, lhs_params


class YearTransform(models.Transform):
    # Use a name that avoids collision with the built-in year lookup.
    lookup_name = 'testyear'

    def as_sql(self, compiler, connection):
        lhs_sql, params = compiler.compile(self.lhs)
        return connection.ops.date_extract_sql('year', lhs_sql), params

    @property
    def output_field(self):
        return models.IntegerField()


@YearTransform.register_lookup
class YearExact(models.lookups.Lookup):
    lookup_name = 'exact'

    def as_sql(self, compiler, connection):
        # We will need to skip the extract part, and instead go
        # directly with the originating field, that is self.lhs.lhs
        lhs_sql, lhs_params = self.process_lhs(compiler, connection, self.lhs.lhs)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        # Note that we must be careful so that we have params in the
        # same order as we have the parts in the SQL.
        params = lhs_params + rhs_params + lhs_params + rhs_params
        # We use PostgreSQL specific SQL here. Note that we must do the
        # conversions in SQL instead of in Python to support F() references.
        return ("%(lhs)s >= (%(rhs)s || '-01-01')::date "
                "AND %(lhs)s <= (%(rhs)s || '-12-31')::date" %
                {'lhs': lhs_sql, 'rhs': rhs_sql}, params)


@YearTransform.register_lookup
class YearLte(models.lookups.LessThanOrEqual):
    """
    The purpose of this lookup is to efficiently compare the year of the field.
    """

    def as_sql(self, compiler, connection):
        # Skip the YearTransform above us (no possibility for efficient
        # lookup otherwise).
        real_lhs = self.lhs.lhs
        lhs_sql, params = self.process_lhs(compiler, connection, real_lhs)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        # Build SQL where the integer year is concatenated with last month
        # and day, then convert that to date. (We try to have SQL like:
        #     WHERE somecol <= '2013-12-31')
        # but also make it work if the rhs_sql is field reference.
        return "%s <= (%s || '-12-31')::date" % (lhs_sql, rhs_sql), params


class Exactly(models.lookups.Exact):
    """
    This lookup is used to test lookup registration.
    """
    lookup_name = 'exactly'

    def get_rhs_op(self, connection, rhs):
        return connection.operators['exact'] % rhs


class SQLFuncMixin:
    def as_sql(self, compiler, connection):
        return '%s()', [self.name]

    @property
    def output_field(self):
        return CustomField()


class SQLFuncLookup(SQLFuncMixin, models.Lookup):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name


class SQLFuncTransform(SQLFuncMixin, models.Transform):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name


class SQLFuncFactory:

    def __init__(self, key, name):
        self.key = key
        self.name = name

    def __call__(self, *args, **kwargs):
        if self.key == 'lookupfunc':
            return SQLFuncLookup(self.name, *args, **kwargs)
        return SQLFuncTransform(self.name, *args, **kwargs)


class CustomField(models.TextField):

    def get_lookup(self, lookup_name):
        if lookup_name.startswith('lookupfunc_'):
            key, name = lookup_name.split('_', 1)
            return SQLFuncFactory(key, name)
        return super().get_lookup(lookup_name)

    def get_transform(self, lookup_name):
        if lookup_name.startswith('transformfunc_'):
            key, name = lookup_name.split('_', 1)
            return SQLFuncFactory(key, name)
        return super().get_transform(lookup_name)


class CustomModel(models.Model):
    field = CustomField()


# We will register this class temporarily in the test method.


class InMonth(models.lookups.Lookup):
    """
    InMonth matches if the column's month is the same as value's month.
    """
    lookup_name = 'inmonth'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        # We need to be careful so that we get the params in right
        # places.
        params = lhs_params + rhs_params + lhs_params + rhs_params
        return ("%s >= date_trunc('month', %s) and "
                "%s < date_trunc('month', %s) + interval '1 months'" %
                (lhs, rhs, lhs, rhs), params)


class DateTimeTransform(models.Transform):
    lookup_name = 'as_datetime'

    @property
    def output_field(self):
        return models.DateTimeField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return 'from_unixtime({})'.format(lhs), params


class LookupTests(TestCase):

    def test_custom_name_lookup(self):
        a1 = Author.objects.create(name='a1', birthdate=date(1981, 2, 16))
        Author.objects.create(name='a2', birthdate=date(2012, 2, 29))
        custom_lookup_name = 'isactually'
        custom_transform_name = 'justtheyear'
        try:
            models.DateField.register_lookup(YearTransform)
            models.DateField.register_lookup(YearTransform, custom_transform_name)
            YearTransform.register_lookup(Exactly)
            YearTransform.register_lookup(Exactly, custom_lookup_name)
            qs1 = Author.objects.filter(birthdate__testyear__exactly=1981)
            qs2 = Author.objects.filter(birthdate__justtheyear__isactually=1981)
            self.assertSequenceEqual(qs1, [a1])
            self.assertSequenceEqual(qs2, [a1])
        finally:
            YearTransform._unregister_lookup(Exactly)
            YearTransform._unregister_lookup(Exactly, custom_lookup_name)
            models.DateField._unregister_lookup(YearTransform)
            models.DateField._unregister_lookup(YearTransform, custom_transform_name)

    def test_custom_exact_lookup_none_rhs(self):
        """
        __exact=None is transformed to __isnull=True if a custom lookup class
        with lookup_name != 'exact' is registered as the `exact` lookup.
        """
        class CustomExactLookup(models.Lookup):
            lookup_name = 'somecustomlookup'

        field = Author._meta.get_field('birthdate')
        OldExactLookup = field.get_lookup('exact')
        author = Author.objects.create(name='author', birthdate=None)
        try:
            type(field).register_lookup(Exactly, 'exact')
            self.assertEqual(Author.objects.get(birthdate__exact=None), author)
        finally:
            type(field).register_lookup(OldExactLookup, 'exact')

    def test_basic_lookup(self):
        a1 = Author.objects.create(name='a1', age=1)
        a2 = Author.objects.create(name='a2', age=2)
        a3 = Author.objects.create(name='a3', age=3)
        a4 = Author.objects.create(name='a4', age=4)
        with register_lookup(models.IntegerField, Div3Lookup):
            self.assertSequenceEqual(Author.objects.filter(age__div3=0), [a3])
            self.assertSequenceEqual(Author.objects.filter(age__div3=1).order_by('age'), [a1, a4])
            self.assertSequenceEqual(Author.objects.filter(age__div3=2), [a2])
            self.assertSequenceEqual(Author.objects.filter(age__div3=3), [])

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific SQL used")
    def test_birthdate_month(self):
        a1 = Author.objects.create(name='a1', birthdate=date(1981, 2, 16))
        a2 = Author.objects.create(name='a2', birthdate=date(2012, 2, 29))
        a3 = Author.objects.create(name='a3', birthdate=date(2012, 1, 31))
        a4 = Author.objects.create(name='a4', birthdate=date(2012, 3, 1))
        with register_lookup(models.DateField, InMonth):
            self.assertSequenceEqual(Author.objects.filter(birthdate__inmonth=date(2012, 1, 15)), [a3])
            self.assertSequenceEqual(Author.objects.filter(birthdate__inmonth=date(2012, 2, 1)), [a2])
            self.assertSequenceEqual(Author.objects.filter(birthdate__inmonth=date(1981, 2, 28)), [a1])
            self.assertSequenceEqual(Author.objects.filter(birthdate__inmonth=date(2012, 3, 12)), [a4])
            self.assertSequenceEqual(Author.objects.filter(birthdate__inmonth=date(2012, 4, 1)), [])

    def test_div3_extract(self):
        with register_lookup(models.IntegerField, Div3Transform):
            a1 = Author.objects.create(name='a1', age=1)
            a2 = Author.objects.create(name='a2', age=2)
            a3 = Author.objects.create(name='a3', age=3)
            a4 = Author.objects.create(name='a4', age=4)
            baseqs = Author.objects.order_by('name')
            self.assertSequenceEqual(baseqs.filter(age__div3=2), [a2])
            self.assertSequenceEqual(baseqs.filter(age__div3__lte=3), [a1, a2, a3, a4])
            self.assertSequenceEqual(baseqs.filter(age__div3__in=[0, 2]), [a2, a3])
            self.assertSequenceEqual(baseqs.filter(age__div3__in=[2, 4]), [a2])
            self.assertSequenceEqual(baseqs.filter(age__div3__gte=3), [])
            self.assertSequenceEqual(baseqs.filter(age__div3__range=(1, 2)), [a1, a2, a4])

    def test_foreignobject_lookup_registration(self):
        field = Article._meta.get_field('author')

        with register_lookup(models.ForeignObject, Exactly):
            self.assertIs(field.get_lookup('exactly'), Exactly)

        # ForeignObject should ignore regular Field lookups
        with register_lookup(models.Field, Exactly):
            self.assertIsNone(field.get_lookup('exactly'))

    def test_lookups_caching(self):
        field = Article._meta.get_field('author')

        # clear and re-cache
        field.get_lookups.cache_clear()
        self.assertNotIn('exactly', field.get_lookups())

        # registration should bust the cache
        with register_lookup(models.ForeignObject, Exactly):
            # getting the lookups again should re-cache
            self.assertIn('exactly', field.get_lookups())


class BilateralTransformTests(TestCase):

    def test_bilateral_upper(self):
        with register_lookup(models.CharField, UpperBilateralTransform):
            Author.objects.bulk_create([
                Author(name='Doe'),
                Author(name='doe'),
                Author(name='Foo'),
            ])
            self.assertQuerysetEqual(
                Author.objects.filter(name__upper='doe'),
                ["<Author: Doe>", "<Author: doe>"], ordered=False)
            self.assertQuerysetEqual(
                Author.objects.filter(name__upper__contains='f'),
                ["<Author: Foo>"], ordered=False)

    def test_bilateral_inner_qs(self):
        with register_lookup(models.CharField, UpperBilateralTransform):
            msg = 'Bilateral transformations on nested querysets are not implemented.'
            with self.assertRaisesMessage(NotImplementedError, msg):
                Author.objects.filter(name__upper__in=Author.objects.values_list('name'))

    def test_bilateral_multi_value(self):
        with register_lookup(models.CharField, UpperBilateralTransform):
            Author.objects.bulk_create([
                Author(name='Foo'),
                Author(name='Bar'),
                Author(name='Ray'),
            ])
            self.assertQuerysetEqual(
                Author.objects.filter(name__upper__in=['foo', 'bar', 'doe']).order_by('name'),
                ['Bar', 'Foo'],
                lambda a: a.name
            )

    def test_div3_bilateral_extract(self):
        with register_lookup(models.IntegerField, Div3BilateralTransform):
            a1 = Author.objects.create(name='a1', age=1)
            a2 = Author.objects.create(name='a2', age=2)
            a3 = Author.objects.create(name='a3', age=3)
            a4 = Author.objects.create(name='a4', age=4)
            baseqs = Author.objects.order_by('name')
            self.assertSequenceEqual(baseqs.filter(age__div3=2), [a2])
            self.assertSequenceEqual(baseqs.filter(age__div3__lte=3), [a3])
            self.assertSequenceEqual(baseqs.filter(age__div3__in=[0, 2]), [a2, a3])
            self.assertSequenceEqual(baseqs.filter(age__div3__in=[2, 4]), [a1, a2, a4])
            self.assertSequenceEqual(baseqs.filter(age__div3__gte=3), [a1, a2, a3, a4])
            self.assertSequenceEqual(baseqs.filter(age__div3__range=(1, 2)), [a1, a2, a4])

    def test_bilateral_order(self):
        with register_lookup(models.IntegerField, Mult3BilateralTransform, Div3BilateralTransform):
            a1 = Author.objects.create(name='a1', age=1)
            a2 = Author.objects.create(name='a2', age=2)
            a3 = Author.objects.create(name='a3', age=3)
            a4 = Author.objects.create(name='a4', age=4)
            baseqs = Author.objects.order_by('name')

            # mult3__div3 always leads to 0
            self.assertSequenceEqual(baseqs.filter(age__mult3__div3=42), [a1, a2, a3, a4])
            self.assertSequenceEqual(baseqs.filter(age__div3__mult3=42), [a3])

    def test_bilateral_fexpr(self):
        with register_lookup(models.IntegerField, Mult3BilateralTransform):
            a1 = Author.objects.create(name='a1', age=1, average_rating=3.2)
            a2 = Author.objects.create(name='a2', age=2, average_rating=0.5)
            a3 = Author.objects.create(name='a3', age=3, average_rating=1.5)
            a4 = Author.objects.create(name='a4', age=4)
            baseqs = Author.objects.order_by('name')
            self.assertSequenceEqual(baseqs.filter(age__mult3=models.F('age')), [a1, a2, a3, a4])
            # Same as age >= average_rating
            self.assertSequenceEqual(baseqs.filter(age__mult3__gte=models.F('average_rating')), [a2, a3])


@override_settings(USE_TZ=True)
class DateTimeLookupTests(TestCase):
    @unittest.skipUnless(connection.vendor == 'mysql', "MySQL specific SQL used")
    def test_datetime_output_field(self):
        with register_lookup(models.PositiveIntegerField, DateTimeTransform):
            ut = MySQLUnixTimestamp.objects.create(timestamp=time.time())
            y2k = timezone.make_aware(datetime(2000, 1, 1))
            self.assertSequenceEqual(MySQLUnixTimestamp.objects.filter(timestamp__as_datetime__gt=y2k), [ut])


class YearLteTests(TestCase):
    def setUp(self):
        models.DateField.register_lookup(YearTransform)
        self.a1 = Author.objects.create(name='a1', birthdate=date(1981, 2, 16))
        self.a2 = Author.objects.create(name='a2', birthdate=date(2012, 2, 29))
        self.a3 = Author.objects.create(name='a3', birthdate=date(2012, 1, 31))
        self.a4 = Author.objects.create(name='a4', birthdate=date(2012, 3, 1))

    def tearDown(self):
        models.DateField._unregister_lookup(YearTransform)

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific SQL used")
    def test_year_lte(self):
        baseqs = Author.objects.order_by('name')
        self.assertSequenceEqual(baseqs.filter(birthdate__testyear__lte=2012), [self.a1, self.a2, self.a3, self.a4])
        self.assertSequenceEqual(baseqs.filter(birthdate__testyear=2012), [self.a2, self.a3, self.a4])

        self.assertNotIn('BETWEEN', str(baseqs.filter(birthdate__testyear=2012).query))
        self.assertSequenceEqual(baseqs.filter(birthdate__testyear__lte=2011), [self.a1])
        # The non-optimized version works, too.
        self.assertSequenceEqual(baseqs.filter(birthdate__testyear__lt=2012), [self.a1])

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific SQL used")
    def test_year_lte_fexpr(self):
        self.a2.age = 2011
        self.a2.save()
        self.a3.age = 2012
        self.a3.save()
        self.a4.age = 2013
        self.a4.save()
        baseqs = Author.objects.order_by('name')
        self.assertSequenceEqual(baseqs.filter(birthdate__testyear__lte=models.F('age')), [self.a3, self.a4])
        self.assertSequenceEqual(baseqs.filter(birthdate__testyear__lt=models.F('age')), [self.a4])

    def test_year_lte_sql(self):
        # This test will just check the generated SQL for __lte. This
        # doesn't require running on PostgreSQL and spots the most likely
        # error - not running YearLte SQL at all.
        baseqs = Author.objects.order_by('name')
        self.assertIn(
            '<= (2011 || ', str(baseqs.filter(birthdate__testyear__lte=2011).query))
        self.assertIn(
            '-12-31', str(baseqs.filter(birthdate__testyear__lte=2011).query))

    def test_postgres_year_exact(self):
        baseqs = Author.objects.order_by('name')
        self.assertIn(
            '= (2011 || ', str(baseqs.filter(birthdate__testyear=2011).query))
        self.assertIn(
            '-12-31', str(baseqs.filter(birthdate__testyear=2011).query))

    def test_custom_implementation_year_exact(self):
        try:
            # Two ways to add a customized implementation for different backends:
            # First is MonkeyPatch of the class.
            def as_custom_sql(self, compiler, connection):
                lhs_sql, lhs_params = self.process_lhs(compiler, connection, self.lhs.lhs)
                rhs_sql, rhs_params = self.process_rhs(compiler, connection)
                params = lhs_params + rhs_params + lhs_params + rhs_params
                return ("%(lhs)s >= str_to_date(concat(%(rhs)s, '-01-01'), '%%%%Y-%%%%m-%%%%d') "
                        "AND %(lhs)s <= str_to_date(concat(%(rhs)s, '-12-31'), '%%%%Y-%%%%m-%%%%d')" %
                        {'lhs': lhs_sql, 'rhs': rhs_sql}, params)
            setattr(YearExact, 'as_' + connection.vendor, as_custom_sql)
            self.assertIn(
                'concat(',
                str(Author.objects.filter(birthdate__testyear=2012).query))
        finally:
            delattr(YearExact, 'as_' + connection.vendor)
        try:
            # The other way is to subclass the original lookup and register the subclassed
            # lookup instead of the original.
            class CustomYearExact(YearExact):
                # This method should be named "as_mysql" for MySQL, "as_postgresql" for postgres
                # and so on, but as we don't know which DB we are running on, we need to use
                # setattr.
                def as_custom_sql(self, compiler, connection):
                    lhs_sql, lhs_params = self.process_lhs(compiler, connection, self.lhs.lhs)
                    rhs_sql, rhs_params = self.process_rhs(compiler, connection)
                    params = lhs_params + rhs_params + lhs_params + rhs_params
                    return ("%(lhs)s >= str_to_date(CONCAT(%(rhs)s, '-01-01'), '%%%%Y-%%%%m-%%%%d') "
                            "AND %(lhs)s <= str_to_date(CONCAT(%(rhs)s, '-12-31'), '%%%%Y-%%%%m-%%%%d')" %
                            {'lhs': lhs_sql, 'rhs': rhs_sql}, params)
            setattr(CustomYearExact, 'as_' + connection.vendor, CustomYearExact.as_custom_sql)
            YearTransform.register_lookup(CustomYearExact)
            self.assertIn(
                'CONCAT(',
                str(Author.objects.filter(birthdate__testyear=2012).query))
        finally:
            YearTransform._unregister_lookup(CustomYearExact)
            YearTransform.register_lookup(YearExact)


class TrackCallsYearTransform(YearTransform):
    # Use a name that avoids collision with the built-in year lookup.
    lookup_name = 'testyear'
    call_order = []

    def as_sql(self, compiler, connection):
        lhs_sql, params = compiler.compile(self.lhs)
        return connection.ops.date_extract_sql('year', lhs_sql), params

    @property
    def output_field(self):
        return models.IntegerField()

    def get_lookup(self, lookup_name):
        self.call_order.append('lookup')
        return super().get_lookup(lookup_name)

    def get_transform(self, lookup_name):
        self.call_order.append('transform')
        return super().get_transform(lookup_name)


class LookupTransformCallOrderTests(TestCase):
    def test_call_order(self):
        with register_lookup(models.DateField, TrackCallsYearTransform):
            # junk lookup - tries lookup, then transform, then fails
            msg = "Unsupported lookup 'junk' for IntegerField or join on the field not permitted."
            with self.assertRaisesMessage(FieldError, msg):
                Author.objects.filter(birthdate__testyear__junk=2012)
            self.assertEqual(TrackCallsYearTransform.call_order,
                             ['lookup', 'transform'])
            TrackCallsYearTransform.call_order = []
            # junk transform - tries transform only, then fails
            with self.assertRaisesMessage(FieldError, msg):
                Author.objects.filter(birthdate__testyear__junk__more_junk=2012)
            self.assertEqual(TrackCallsYearTransform.call_order,
                             ['transform'])
            TrackCallsYearTransform.call_order = []
            # Just getting the year (implied __exact) - lookup only
            Author.objects.filter(birthdate__testyear=2012)
            self.assertEqual(TrackCallsYearTransform.call_order,
                             ['lookup'])
            TrackCallsYearTransform.call_order = []
            # Just getting the year (explicit __exact) - lookup only
            Author.objects.filter(birthdate__testyear__exact=2012)
            self.assertEqual(TrackCallsYearTransform.call_order,
                             ['lookup'])


class CustomisedMethodsTests(TestCase):

    def test_overridden_get_lookup(self):
        q = CustomModel.objects.filter(field__lookupfunc_monkeys=3)
        self.assertIn('monkeys()', str(q.query))

    def test_overridden_get_transform(self):
        q = CustomModel.objects.filter(field__transformfunc_banana=3)
        self.assertIn('banana()', str(q.query))

    def test_overridden_get_lookup_chain(self):
        q = CustomModel.objects.filter(field__transformfunc_banana__lookupfunc_elephants=3)
        self.assertIn('elephants()', str(q.query))

    def test_overridden_get_transform_chain(self):
        q = CustomModel.objects.filter(field__transformfunc_banana__transformfunc_pear=3)
        self.assertIn('pear()', str(q.query))


class SubqueryTransformTests(TestCase):
    def test_subquery_usage(self):
        with register_lookup(models.IntegerField, Div3Transform):
            Author.objects.create(name='a1', age=1)
            a2 = Author.objects.create(name='a2', age=2)
            Author.objects.create(name='a3', age=3)
            Author.objects.create(name='a4', age=4)
            qs = Author.objects.order_by('name').filter(id__in=Author.objects.filter(age__div3=2))
            self.assertSequenceEqual(qs, [a2])

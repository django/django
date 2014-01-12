from datetime import date
import unittest

from django.test import TestCase
from .models import Author
from django.db import models
from django.db import connection


class Div3Lookup(models.Lookup):
    lookup_name = 'div3'

    def as_sql(self, qn, connection):
        lhs, params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params.extend(rhs_params)
        return '%s %%%% 3 = %s' % (lhs, rhs), params


class Div3Transform(models.Transform):
    lookup_name = 'div3'

    def as_sql(self, qn, connection):
        lhs, lhs_params = qn.compile(self.lhs)
        return '%s %%%% 3' % (lhs,), lhs_params


class YearTransform(models.Transform):
    lookup_name = 'year'

    def as_sql(self, qn, connection):
        lhs_sql, params = qn.compile(self.lhs)
        return connection.ops.date_extract_sql('year', lhs_sql), params

    @property
    def output_type(self):
        return models.IntegerField()


class YearExact(models.lookups.Lookup):
    lookup_name = 'exact'

    def as_sql(self, qn, connection):
        # We will need to skip the extract part, and instead go
        # directly with the originating field, that is self.lhs.lhs
        lhs_sql, lhs_params = self.process_lhs(qn, connection, self.lhs.lhs)
        rhs_sql, rhs_params = self.process_rhs(qn, connection)
        # Note that we must be careful so that we have params in the
        # same order as we have the parts in the SQL.
        params = lhs_params + rhs_params + lhs_params + rhs_params
        # We use PostgreSQL specific SQL here. Note that we must do the
        # conversions in SQL instead of in Python to support F() references.
        return ("%(lhs)s >= (%(rhs)s || '-01-01')::date "
                "AND %(lhs)s <= (%(rhs)s || '-12-31')::date" %
                {'lhs': lhs_sql, 'rhs': rhs_sql}, params)
YearTransform.register_lookup(YearExact)


class YearLte(models.lookups.LessThanOrEqual):
    """
    The purpose of this lookup is to efficiently compare the year of the field.
    """

    def as_sql(self, qn, connection):
        # Skip the YearTransform above us (no possibility for efficient
        # lookup otherwise).
        real_lhs = self.lhs.lhs
        lhs_sql, params = self.process_lhs(qn, connection, real_lhs)
        rhs_sql, rhs_params = self.process_rhs(qn, connection)
        params.extend(rhs_params)
        # Build SQL where the integer year is concatenated with last month
        # and day, then convert that to date. (We try to have SQL like:
        #     WHERE somecol <= '2013-12-31')
        # but also make it work if the rhs_sql is field reference.
        return "%s <= (%s || '-12-31')::date" % (lhs_sql, rhs_sql), params
YearTransform.register_lookup(YearLte)


# We will register this class temporarily in the test method.


class InMonth(models.lookups.Lookup):
    """
    InMonth matches if the column's month is the same as value's month.
    """
    lookup_name = 'inmonth'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        # We need to be careful so that we get the params in right
        # places.
        params = lhs_params + rhs_params + lhs_params + rhs_params
        return ("%s >= date_trunc('month', %s) and "
                "%s < date_trunc('month', %s) + interval '1 months'" %
                (lhs, rhs, lhs, rhs), params)


class LookupTests(TestCase):
    def test_basic_lookup(self):
        a1 = Author.objects.create(name='a1', age=1)
        a2 = Author.objects.create(name='a2', age=2)
        a3 = Author.objects.create(name='a3', age=3)
        a4 = Author.objects.create(name='a4', age=4)
        models.IntegerField.register_lookup(Div3Lookup)
        try:
            self.assertQuerysetEqual(
                Author.objects.filter(age__div3=0),
                [a3], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(age__div3=1).order_by('age'),
                [a1, a4], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(age__div3=2),
                [a2], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(age__div3=3),
                [], lambda x: x
            )
        finally:
            models.IntegerField._unregister_lookup(Div3Lookup)

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific SQL used")
    def test_birthdate_month(self):
        a1 = Author.objects.create(name='a1', birthdate=date(1981, 2, 16))
        a2 = Author.objects.create(name='a2', birthdate=date(2012, 2, 29))
        a3 = Author.objects.create(name='a3', birthdate=date(2012, 1, 31))
        a4 = Author.objects.create(name='a4', birthdate=date(2012, 3, 1))
        models.DateField.register_lookup(InMonth)
        try:
            self.assertQuerysetEqual(
                Author.objects.filter(birthdate__inmonth=date(2012, 1, 15)),
                [a3], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(birthdate__inmonth=date(2012, 2, 1)),
                [a2], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(birthdate__inmonth=date(1981, 2, 28)),
                [a1], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(birthdate__inmonth=date(2012, 3, 12)),
                [a4], lambda x: x
            )
            self.assertQuerysetEqual(
                Author.objects.filter(birthdate__inmonth=date(2012, 4, 1)),
                [], lambda x: x
            )
        finally:
            models.DateField._unregister_lookup(InMonth)

    def test_div3_extract(self):
        models.IntegerField.register_lookup(Div3Transform)
        try:
            a1 = Author.objects.create(name='a1', age=1)
            a2 = Author.objects.create(name='a2', age=2)
            a3 = Author.objects.create(name='a3', age=3)
            a4 = Author.objects.create(name='a4', age=4)
            baseqs = Author.objects.order_by('name')
            self.assertQuerysetEqual(
                baseqs.filter(age__div3=2),
                [a2], lambda x: x)
            self.assertQuerysetEqual(
                baseqs.filter(age__div3__lte=3),
                [a1, a2, a3, a4], lambda x: x)
            self.assertQuerysetEqual(
                baseqs.filter(age__div3__in=[0, 2]),
                [a2, a3], lambda x: x)
        finally:
            models.IntegerField._unregister_lookup(Div3Transform)


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
        self.assertQuerysetEqual(
            baseqs.filter(birthdate__year__lte=2012),
            [self.a1, self.a2, self.a3, self.a4], lambda x: x)
        self.assertQuerysetEqual(
            baseqs.filter(birthdate__year=2012),
            [self.a2, self.a3, self.a4], lambda x: x)

        self.assertNotIn('BETWEEN', str(baseqs.filter(birthdate__year=2012).query))
        self.assertQuerysetEqual(
            baseqs.filter(birthdate__year__lte=2011),
            [self.a1], lambda x: x)
        # The non-optimized version works, too.
        self.assertQuerysetEqual(
            baseqs.filter(birthdate__year__lt=2012),
            [self.a1], lambda x: x)

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific SQL used")
    def test_year_lte_fexpr(self):
        self.a2.age = 2011
        self.a2.save()
        self.a3.age = 2012
        self.a3.save()
        self.a4.age = 2013
        self.a4.save()
        baseqs = Author.objects.order_by('name')
        self.assertQuerysetEqual(
            baseqs.filter(birthdate__year__lte=models.F('age')),
            [self.a3, self.a4], lambda x: x)
        self.assertQuerysetEqual(
            baseqs.filter(birthdate__year__lt=models.F('age')),
            [self.a4], lambda x: x)

    def test_year_lte_sql(self):
        # This test will just check the generated SQL for __lte. This
        # doesn't require running on PostgreSQL and spots the most likely
        # error - not running YearLte SQL at all.
        baseqs = Author.objects.order_by('name')
        self.assertIn(
            '<= (2011 || ', str(baseqs.filter(birthdate__year__lte=2011).query))
        self.assertIn(
            '-12-31', str(baseqs.filter(birthdate__year__lte=2011).query))

    def test_postgres_year_exact(self):
        baseqs = Author.objects.order_by('name')
        self.assertIn(
            '= (2011 || ', str(baseqs.filter(birthdate__year=2011).query))
        self.assertIn(
            '-12-31', str(baseqs.filter(birthdate__year=2011).query))

    def test_custom_implementation_year_exact(self):
        try:
            # Two ways to add a customized implementation for different backends:
            # First is MonkeyPatch of the class.
            def as_custom_sql(self, qn, connection):
                lhs_sql, lhs_params = self.process_lhs(qn, connection, self.lhs.lhs)
                rhs_sql, rhs_params = self.process_rhs(qn, connection)
                params = lhs_params + rhs_params + lhs_params + rhs_params
                return ("%(lhs)s >= str_to_date(concat(%(rhs)s, '-01-01'), '%%%%Y-%%%%m-%%%%d') "
                        "AND %(lhs)s <= str_to_date(concat(%(rhs)s, '-12-31'), '%%%%Y-%%%%m-%%%%d')" %
                        {'lhs': lhs_sql, 'rhs': rhs_sql}, params)
            setattr(YearExact, 'as_' + connection.vendor, as_custom_sql)
            self.assertIn(
                'concat(',
                str(Author.objects.filter(birthdate__year=2012).query))
        finally:
            delattr(YearExact, 'as_' + connection.vendor)
        try:
            # The other way is to subclass the original lookup and register the subclassed
            # lookup instead of the original.
            class CustomYearExact(YearExact):
                # This method should be named "as_mysql" for MySQL, "as_postgresql" for postgres
                # and so on, but as we don't know which DB we are running on, we need to use
                # setattr.
                def as_custom_sql(self, qn, connection):
                    lhs_sql, lhs_params = self.process_lhs(qn, connection, self.lhs.lhs)
                    rhs_sql, rhs_params = self.process_rhs(qn, connection)
                    params = lhs_params + rhs_params + lhs_params + rhs_params
                    return ("%(lhs)s >= str_to_date(CONCAT(%(rhs)s, '-01-01'), '%%%%Y-%%%%m-%%%%d') "
                            "AND %(lhs)s <= str_to_date(CONCAT(%(rhs)s, '-12-31'), '%%%%Y-%%%%m-%%%%d')" %
                            {'lhs': lhs_sql, 'rhs': rhs_sql}, params)
            setattr(CustomYearExact, 'as_' + connection.vendor, CustomYearExact.as_custom_sql)
            YearTransform.register_lookup(CustomYearExact)
            self.assertIn(
                'CONCAT(',
                str(Author.objects.filter(birthdate__year=2012).query))
        finally:
            YearTransform._unregister_lookup(CustomYearExact)
            YearTransform.register_lookup(YearExact)

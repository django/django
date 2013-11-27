from copy import copy
from datetime import date
import unittest

from django.test import TestCase
from .models import Author
from django.db import models
from django.db import connection
from django.db.backends.utils import add_implementation


class Div3Lookup(models.lookups.Lookup):
    lookup_name = 'div3'

    def as_sql(self, qn, connection):
        lhs, params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params.extend(rhs_params)
        return '%s %%%% 3 = %s' % (lhs, rhs), params


class InMonth(models.lookups.Lookup):
    """
    InMonth matches if the column's month is contained in the value's month.
    """
    lookup_name = 'inmonth'

    def as_sql(self, qn, connection):
        lhs, params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        # We need to be careful so that we get the params in right
        # places.
        full_params = params[:]
        full_params.extend(rhs_params)
        full_params.extend(params)
        full_params.extend(rhs_params)
        return ("%s >= date_trunc('month', %s) and "
                "%s < date_trunc('month', %s) + interval '1 months'" %
                (lhs, rhs, lhs, rhs), full_params)


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

    def test_custom_compiles(self):
        a1 = Author.objects.create(name='a1', age=1)
        a2 = Author.objects.create(name='a2', age=2)
        a3 = Author.objects.create(name='a3', age=3)
        a4 = Author.objects.create(name='a4', age=4)

        class AnotherEqual(models.lookups.Exact):
            lookup_name = 'anotherequal'
        models.Field.register_lookup(AnotherEqual)
        try:
            @add_implementation(AnotherEqual, connection.vendor)
            def custom_eq_sql(node, compiler):
                return '1 = 1', []

            self.assertIn('1 = 1', str(Author.objects.filter(name__anotherequal='asdf').query))
            self.assertQuerysetEqual(
                Author.objects.filter(name__anotherequal='asdf').order_by('name'),
                [a1, a2, a3, a4], lambda x: x)

            @add_implementation(AnotherEqual, connection.vendor)
            def another_custom_eq_sql(node, compiler):
                # If you need to override one method, it seems this is the best
                # option.
                node = copy(node)

                class OverriddenAnotherEqual(AnotherEqual):
                    def get_rhs_op(self, connection, rhs):
                        return ' <> %s'
                node.__class__ = OverriddenAnotherEqual
                return node.as_sql(compiler, compiler.connection)
            self.assertIn(' <> ', str(Author.objects.filter(name__anotherequal='a1').query))
            self.assertQuerysetEqual(
                Author.objects.filter(name__anotherequal='a1').order_by('name'),
                [a2, a3, a4], lambda x: x
            )
        finally:
            models.Field._unregister_lookup(AnotherEqual)

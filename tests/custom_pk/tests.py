# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.db import transaction, IntegrityError
from django.test import TestCase, skipIfDBFeature
from django.utils import six

from .models import Employee, Business, Bar, Foo


class CustomPKTests(TestCase):
    def test_custom_pk(self):
        dan = Employee.objects.create(
            employee_code=123, first_name="Dan", last_name="Jones"
        )
        self.assertQuerysetEqual(
            Employee.objects.all(), [
                "Dan Jones",
            ],
            six.text_type
        )

        fran = Employee.objects.create(
            employee_code=456, first_name="Fran", last_name="Bones"
        )
        self.assertQuerysetEqual(
            Employee.objects.all(), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type
        )

        self.assertEqual(Employee.objects.get(pk=123), dan)
        self.assertEqual(Employee.objects.get(pk=456), fran)

        self.assertRaises(Employee.DoesNotExist,
            lambda: Employee.objects.get(pk=42)
        )

        # Use the name of the primary key, rather than pk.
        self.assertEqual(Employee.objects.get(employee_code=123), dan)
        # pk can be used as a substitute for the primary key.
        self.assertQuerysetEqual(
            Employee.objects.filter(pk__in=[123, 456]), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type
        )
        # The primary key can be accessed via the pk property on the model.
        e = Employee.objects.get(pk=123)
        self.assertEqual(e.pk, 123)
        # Or we can use the real attribute name for the primary key:
        self.assertEqual(e.employee_code, 123)

        # Fran got married and changed her last name.
        fran = Employee.objects.get(pk=456)
        fran.last_name = "Jones"
        fran.save()

        self.assertQuerysetEqual(
            Employee.objects.filter(last_name="Jones"), [
                "Dan Jones",
                "Fran Jones",
            ],
            six.text_type
        )

        emps = Employee.objects.in_bulk([123, 456])
        self.assertEqual(emps[123], dan)

        b = Business.objects.create(name="Sears")
        b.employees.add(dan, fran)
        self.assertQuerysetEqual(
            b.employees.all(), [
                "Dan Jones",
                "Fran Jones",
            ],
            six.text_type
        )
        self.assertQuerysetEqual(
            fran.business_set.all(), [
                "Sears",
            ],
            lambda b: b.name
        )

        self.assertEqual(Business.objects.in_bulk(["Sears"]), {
            "Sears": b,
        })

        self.assertQuerysetEqual(
            Business.objects.filter(name="Sears"), [
                "Sears"
            ],
            lambda b: b.name
        )
        self.assertQuerysetEqual(
            Business.objects.filter(pk="Sears"), [
                "Sears",
            ],
            lambda b: b.name
        )

        # Queries across tables, involving primary key
        self.assertQuerysetEqual(
            Employee.objects.filter(business__name="Sears"), [
                "Dan Jones",
                "Fran Jones",
            ],
            six.text_type,
        )
        self.assertQuerysetEqual(
            Employee.objects.filter(business__pk="Sears"), [
                "Dan Jones",
                "Fran Jones",
            ],
            six.text_type,
        )

        self.assertQuerysetEqual(
            Business.objects.filter(employees__employee_code=123), [
                "Sears",
            ],
            lambda b: b.name
        )
        self.assertQuerysetEqual(
            Business.objects.filter(employees__pk=123), [
                "Sears",
            ],
            lambda b: b.name,
        )

        self.assertQuerysetEqual(
            Business.objects.filter(employees__first_name__startswith="Fran"), [
                "Sears",
            ],
            lambda b: b.name
        )

    def test_unicode_pk(self):
        # Primary key may be unicode string
        bus = Business.objects.create(name='jaźń')

    def test_unique_pk(self):
        # The primary key must also obviously be unique, so trying to create a
        # new object with the same primary key will fail.
        e = Employee.objects.create(
            employee_code=123, first_name="Frank", last_name="Jones"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(employee_code=123, first_name="Fred", last_name="Jones")

    def test_custom_field_pk(self):
        # Regression for #10785 -- Custom fields can be used for primary keys.
        new_bar = Bar.objects.create()
        new_foo = Foo.objects.create(bar=new_bar)

        f = Foo.objects.get(bar=new_bar.pk)
        self.assertEqual(f, new_foo)
        self.assertEqual(f.bar, new_bar)

        f = Foo.objects.get(bar=new_bar)
        self.assertEqual(f, new_foo),
        self.assertEqual(f.bar, new_bar)

    # SQLite lets objects be saved with an empty primary key, even though an
    # integer is expected. So we can't check for an error being raised in that
    # case for SQLite. Remove it from the suite for this next bit.
    @skipIfDBFeature('supports_unspecified_pk')
    def test_required_pk(self):
        # The primary key must be specified, so an error is raised if you
        # try to create an object without it.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(first_name="Tom", last_name="Smith")

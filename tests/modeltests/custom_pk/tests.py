# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils.unittest import skipIf
from django.conf import settings
from django.db import transaction, IntegrityError, DEFAULT_DB_ALIAS

from models import Employee, Business, Bar, Foo

class CustomPkTestCase(TestCase):
    #no fixture here because MyWrapper doesn't serialize nicely

    def test_custom_pk(self):
        dan = Employee(employee_code=123, first_name='Dan', last_name='Jones')
        dan.save()
        self.assertQuerysetEqual(Employee.objects.all(),
                                 ['<Employee: Dan Jones>'])

        fran = Employee(employee_code=456, first_name='Fran', last_name='Bones')
        fran.save()
        self.assertQuerysetEqual(Employee.objects.all(),
                                 ['<Employee: Fran Bones>', '<Employee: Dan Jones>'])

        self.assertEqual(repr(Employee.objects.get(pk=123)),
                         '<Employee: Dan Jones>')
        self.assertEqual(repr(Employee.objects.get(pk=456)),
                         '<Employee: Fran Bones>')

        self.assertRaises(Employee.DoesNotExist,
                          Employee.objects.get, pk=42)

        # Use the name of the primary key, rather than pk.
        self.assertEqual(repr(Employee.objects.get(employee_code__exact=123)),
                         '<Employee: Dan Jones>')

        # pk can be used as a substitute for the primary key.
        self.assertQuerysetEqual(Employee.objects.filter(pk__in=[123, 456]),
                                 ['<Employee: Fran Bones>', '<Employee: Dan Jones>'])

        # The primary key can be accessed via the pk property on the model.
        e = Employee.objects.get(pk=123)
        self.assertEqual(e.pk, 123)

        # Or we can use the real attribute name for the primary key:
        self.assertEqual(e.employee_code, 123)

        # Fran got married and changed her last name.
        fran = Employee.objects.get(pk=456)
        fran.last_name = 'Jones'
        fran.save()

        self.assertQuerysetEqual(Employee.objects.filter(last_name__exact='Jones') ,
                                 ['<Employee: Dan Jones>', '<Employee: Fran Jones>'])

        emps = Employee.objects.in_bulk([123, 456])
        self.assertEqual(repr(emps[123]),
                         '<Employee: Dan Jones>')


        b = Business(name='Sears')
        b.save()
        b.employees.add(dan, fran)
        self.assertQuerysetEqual(b.employees.all(),
                                 ['<Employee: Dan Jones>', '<Employee: Fran Jones>'])
        self.assertQuerysetEqual(fran.business_set.all(),
                                 ['<Business: Sears>'])
        self.assertEqual(repr(Business.objects.in_bulk(['Sears'])),
                         "{u'Sears': <Business: Sears>}")

        self.assertQuerysetEqual(Business.objects.filter(name__exact='Sears'),
                                 ['<Business: Sears>'])
        self.assertQuerysetEqual(Business.objects.filter(pk='Sears'),
                                 ['<Business: Sears>'])

        # Queries across tables, involving primary key
        self.assertQuerysetEqual(Employee.objects.filter(business__name__exact='Sears'),
                                 ['<Employee: Dan Jones>', '<Employee: Fran Jones>'])
        self.assertQuerysetEqual(Employee.objects.filter(business__pk='Sears'),
                                 ['<Employee: Dan Jones>', '<Employee: Fran Jones>'])

        self.assertQuerysetEqual(Business.objects.filter(employees__employee_code__exact=123),
                                 ['<Business: Sears>'])
        self.assertQuerysetEqual(Business.objects.filter(employees__pk=123),
                                 ['<Business: Sears>'])
        self.assertQuerysetEqual(Business.objects.filter(employees__first_name__startswith='Fran'),
                                 ['<Business: Sears>'])

    def test_unicode_pk(self):
        # Primary key may be unicode string
        bus = Business(name=u'jaźń')
        bus.save()

    def test_unique_primary_key(self):
        # The primary key must also obviously be unique, so trying to create a new
        # object with the same primary key will fail.
        e = Employee.objects.create(employee_code=123, first_name='Alex', last_name='Gaynor')
        e.save()
        self.assertRaises(IntegrityError,        
                          Employee.objects.create,
                          employee_code=123, first_name='Russell', last_name='KM')


    def test_custom_fields_can_be_primary_keys(self):
        # Regression for #10785 -- Custom fields can be used for primary keys.
        new_bar = Bar.objects.create()
        new_foo = Foo.objects.create(bar=new_bar)

        #works because of changes in get_db_prep_lookup
        f = Foo.objects.get(bar=new_bar.pk)
        self.assertEqual(f, new_foo)
        self.assertEqual(f.bar, new_bar)

        f = Foo.objects.get(bar=new_bar)
        self.assertEqual(f, new_foo)
        self.assertEqual(f.bar, new_bar)

    # SQLite lets objects be saved with an empty primary key, even though an
    # integer is expected. So we can't check for an error being raised in that case
    # for SQLite. Remove it from the suite for this next bit.
    @skipIf(settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.sqlite3',
            "SQLite lets objects be saved with empty pk")
    def test_empty_pk_error(self):
        self.assertRaises(IntegrityError,
                          Employee.objects.create,
                          first_name='Tom', last_name='Smith')
            

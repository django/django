from __future__ import absolute_import

from django.core.exceptions import FieldError
from django.db.models import F
from django.test import TestCase

from .models import Company, Employee


class ExpressionsTests(TestCase):
    def test_filter(self):
        Company.objects.create(
            name="Example Inc.", num_employees=2300, num_chairs=5,
            ceo=Employee.objects.create(firstname="Joe", lastname="Smith")
        )
        Company.objects.create(
            name="Foobar Ltd.", num_employees=3, num_chairs=4,
            ceo=Employee.objects.create(firstname="Frank", lastname="Meyer")
        )
        Company.objects.create(
            name="Test GmbH", num_employees=32, num_chairs=1,
            ceo=Employee.objects.create(firstname="Max", lastname="Mustermann")
        )

        company_query = Company.objects.values(
            "name", "num_employees", "num_chairs"
        ).order_by(
            "name", "num_employees", "num_chairs"
        )

        # We can filter for companies where the number of employees is greater
        # than the number of chairs.
        self.assertQuerysetEqual(
            company_query.filter(num_employees__gt=F("num_chairs")), [
                {
                    "num_chairs": 5,
                    "name": "Example Inc.",
                    "num_employees": 2300,
                },
                {
                    "num_chairs": 1,
                    "name": "Test GmbH",
                    "num_employees": 32
                },
            ],
            lambda o: o
        )

        # We can set one field to have the value of another field
        # Make sure we have enough chairs
        company_query.update(num_chairs=F("num_employees"))
        self.assertQuerysetEqual(
            company_query, [
                {
                    "num_chairs": 2300,
                    "name": "Example Inc.",
                    "num_employees": 2300
                },
                {
                    "num_chairs": 3,
                    "name": "Foobar Ltd.",
                    "num_employees": 3
                },
                {
                    "num_chairs": 32,
                    "name": "Test GmbH",
                    "num_employees": 32
                }
            ],
            lambda o: o
        )

        # We can perform arithmetic operations in expressions
        # Make sure we have 2 spare chairs
        company_query.update(num_chairs=F("num_employees")+2)
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 2302,
                    'name': u'Example Inc.',
                    'num_employees': 2300
                },
                {
                    'num_chairs': 5,
                    'name': u'Foobar Ltd.',
                    'num_employees': 3
                },
                {
                    'num_chairs': 34,
                    'name': u'Test GmbH',
                    'num_employees': 32
                }
            ],
            lambda o: o,
        )

        # Law of order of operations is followed
        company_query.update(
            num_chairs=F('num_employees') + 2 * F('num_employees')
        )
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 6900,
                    'name': u'Example Inc.',
                    'num_employees': 2300
                },
                {
                    'num_chairs': 9,
                    'name': u'Foobar Ltd.',
                    'num_employees': 3
                },
                {
                    'num_chairs': 96,
                    'name': u'Test GmbH',
                    'num_employees': 32
                }
            ],
            lambda o: o,
        )

        # Law of order of operations can be overridden by parentheses
        company_query.update(
            num_chairs=((F('num_employees') + 2) * F('num_employees'))
        )
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 5294600,
                    'name': u'Example Inc.',
                    'num_employees': 2300
                },
                {
                    'num_chairs': 15,
                    'name': u'Foobar Ltd.',
                    'num_employees': 3
                },
                {
                    'num_chairs': 1088,
                    'name': u'Test GmbH',
                    'num_employees': 32
                }
            ],
            lambda o: o,
        )

        # The relation of a foreign key can become copied over to an other
        # foreign key.
        self.assertEqual(
            Company.objects.update(point_of_contact=F('ceo')),
            3
        )
        self.assertQuerysetEqual(
            Company.objects.all(), [
                "Joe Smith",
                "Frank Meyer",
                "Max Mustermann",
            ],
            lambda c: unicode(c.point_of_contact),
        )

        c = Company.objects.all()[0]
        c.point_of_contact = Employee.objects.create(firstname="Guido", lastname="van Rossum")
        c.save()

        # F Expressions can also span joins
        self.assertQuerysetEqual(
            Company.objects.filter(ceo__firstname=F("point_of_contact__firstname")), [
                "Foobar Ltd.",
                "Test GmbH",
            ],
            lambda c: c.name
        )

        Company.objects.exclude(
            ceo__firstname=F("point_of_contact__firstname")
        ).update(name="foo")
        self.assertEqual(
            Company.objects.exclude(
                ceo__firstname=F('point_of_contact__firstname')
            ).get().name,
            "foo",
        )

        self.assertRaises(FieldError,
            lambda: Company.objects.exclude(
                ceo__firstname=F('point_of_contact__firstname')
            ).update(name=F('point_of_contact__lastname'))
        )

        # F expressions can be used to update attributes on single objects
        test_gmbh = Company.objects.get(name="Test GmbH")
        self.assertEqual(test_gmbh.num_employees, 32)
        test_gmbh.num_employees = F("num_employees") + 4
        test_gmbh.save()
        test_gmbh = Company.objects.get(pk=test_gmbh.pk)
        self.assertEqual(test_gmbh.num_employees, 36)

        # F expressions cannot be used to update attributes which are foreign
        # keys, or attributes which involve joins.
        test_gmbh.point_of_contact = None
        test_gmbh.save()
        self.assertTrue(test_gmbh.point_of_contact is None)
        def test():
            test_gmbh.point_of_contact = F("ceo")
        self.assertRaises(ValueError, test)

        test_gmbh.point_of_contact = test_gmbh.ceo
        test_gmbh.save()
        test_gmbh.name = F("ceo__last_name")
        self.assertRaises(FieldError, test_gmbh.save)

        # F expressions cannot be used to update attributes on objects which do
        # not yet exist in the database
        acme = Company(
            name="The Acme Widget Co.", num_employees=12, num_chairs=5,
            ceo=test_gmbh.ceo
        )
        acme.num_employees = F("num_employees") + 16
        self.assertRaises(TypeError, acme.save)

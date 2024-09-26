import unittest

from django.db import NotSupportedError, connection
from django.db.models import F
from django.db.models.fields.tuple_lookups import (
    TupleExact,
    TupleGreaterThan,
    TupleGreaterThanOrEqual,
    TupleIn,
    TupleIsNull,
    TupleLessThan,
    TupleLessThanOrEqual,
)
from django.test import TestCase

from .models import Contact, Customer


class TupleLookupsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.customer_1 = Customer.objects.create(customer_id=1, company="a")
        cls.customer_2 = Customer.objects.create(customer_id=1, company="b")
        cls.customer_3 = Customer.objects.create(customer_id=2, company="c")
        cls.customer_4 = Customer.objects.create(customer_id=3, company="d")
        cls.customer_5 = Customer.objects.create(customer_id=1, company="e")
        cls.contact_1 = Contact.objects.create(customer=cls.customer_1)
        cls.contact_2 = Contact.objects.create(customer=cls.customer_1)
        cls.contact_3 = Contact.objects.create(customer=cls.customer_2)
        cls.contact_4 = Contact.objects.create(customer=cls.customer_3)
        cls.contact_5 = Contact.objects.create(customer=cls.customer_1)
        cls.contact_6 = Contact.objects.create(customer=cls.customer_5)

    def test_exact(self):
        test_cases = (
            (self.customer_1, (self.contact_1, self.contact_2, self.contact_5)),
            (self.customer_2, (self.contact_3,)),
            (self.customer_3, (self.contact_4,)),
            (self.customer_4, ()),
            (self.customer_5, (self.contact_6,)),
        )

        for customer, contacts in test_cases:
            with self.subTest(
                "filter(customer=customer)",
                customer=customer,
                contacts=contacts,
            ):
                self.assertSequenceEqual(
                    Contact.objects.filter(customer=customer).order_by("id"), contacts
                )
            with self.subTest(
                "filter(TupleExact)",
                customer=customer,
                contacts=contacts,
            ):
                lhs = (F("customer_code"), F("company_code"))
                rhs = (customer.customer_id, customer.company)
                lookup = TupleExact(lhs, rhs)
                self.assertSequenceEqual(
                    Contact.objects.filter(lookup).order_by("id"), contacts
                )

    def test_exact_subquery(self):
        with self.assertRaisesMessage(
            NotSupportedError, "'exact' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer=subquery).order_by("id"), ()
            )

    def test_in(self):
        cust_1, cust_2, cust_3, cust_4, cust_5 = (
            self.customer_1,
            self.customer_2,
            self.customer_3,
            self.customer_4,
            self.customer_5,
        )
        c1, c2, c3, c4, c5, c6 = (
            self.contact_1,
            self.contact_2,
            self.contact_3,
            self.contact_4,
            self.contact_5,
            self.contact_6,
        )
        test_cases = (
            ((), ()),
            ((cust_1,), (c1, c2, c5)),
            ((cust_1, cust_2), (c1, c2, c3, c5)),
            ((cust_1, cust_2, cust_3), (c1, c2, c3, c4, c5)),
            ((cust_1, cust_2, cust_3, cust_4), (c1, c2, c3, c4, c5)),
            ((cust_1, cust_2, cust_3, cust_4, cust_5), (c1, c2, c3, c4, c5, c6)),
        )

        for customers, contacts in test_cases:
            with self.subTest(
                "filter(customer__in=customers)",
                customers=customers,
                contacts=contacts,
            ):
                self.assertSequenceEqual(
                    Contact.objects.filter(customer__in=customers).order_by("id"),
                    contacts,
                )
            with self.subTest(
                "filter(TupleIn)",
                customers=customers,
                contacts=contacts,
            ):
                lhs = (F("customer_code"), F("company_code"))
                rhs = [(c.customer_id, c.company) for c in customers]
                lookup = TupleIn(lhs, rhs)
                self.assertSequenceEqual(
                    Contact.objects.filter(lookup).order_by("id"), contacts
                )

    @unittest.skipIf(
        connection.vendor == "mysql",
        "MySQL doesn't support LIMIT & IN/ALL/ANY/SOME subquery",
    )
    def test_in_subquery(self):
        subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
        self.assertSequenceEqual(
            Contact.objects.filter(customer__in=subquery).order_by("id"),
            (self.contact_1, self.contact_2, self.contact_5),
        )

    def test_lt(self):
        c1, c2, c3, c4, c5, c6 = (
            self.contact_1,
            self.contact_2,
            self.contact_3,
            self.contact_4,
            self.contact_5,
            self.contact_6,
        )
        test_cases = (
            (self.customer_1, ()),
            (self.customer_2, (c1, c2, c5)),
            (self.customer_5, (c1, c2, c3, c5)),
            (self.customer_3, (c1, c2, c3, c5, c6)),
            (self.customer_4, (c1, c2, c3, c4, c5, c6)),
        )

        for customer, contacts in test_cases:
            with self.subTest(
                "filter(customer__lt=customer)",
                customer=customer,
                contacts=contacts,
            ):
                self.assertSequenceEqual(
                    Contact.objects.filter(customer__lt=customer).order_by("id"),
                    contacts,
                )
            with self.subTest(
                "filter(TupleLessThan)",
                customer=customer,
                contacts=contacts,
            ):
                lhs = (F("customer_code"), F("company_code"))
                rhs = (customer.customer_id, customer.company)
                lookup = TupleLessThan(lhs, rhs)
                self.assertSequenceEqual(
                    Contact.objects.filter(lookup).order_by("id"), contacts
                )

    def test_lt_subquery(self):
        with self.assertRaisesMessage(
            NotSupportedError, "'lt' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer__lt=subquery).order_by("id"), ()
            )

    def test_lte(self):
        c1, c2, c3, c4, c5, c6 = (
            self.contact_1,
            self.contact_2,
            self.contact_3,
            self.contact_4,
            self.contact_5,
            self.contact_6,
        )
        test_cases = (
            (self.customer_1, (c1, c2, c5)),
            (self.customer_2, (c1, c2, c3, c5)),
            (self.customer_5, (c1, c2, c3, c5, c6)),
            (self.customer_3, (c1, c2, c3, c4, c5, c6)),
            (self.customer_4, (c1, c2, c3, c4, c5, c6)),
        )

        for customer, contacts in test_cases:
            with self.subTest(
                "filter(customer__lte=customer)",
                customer=customer,
                contacts=contacts,
            ):
                self.assertSequenceEqual(
                    Contact.objects.filter(customer__lte=customer).order_by("id"),
                    contacts,
                )
            with self.subTest(
                "filter(TupleLessThanOrEqual)",
                customer=customer,
                contacts=contacts,
            ):
                lhs = (F("customer_code"), F("company_code"))
                rhs = (customer.customer_id, customer.company)
                lookup = TupleLessThanOrEqual(lhs, rhs)
                self.assertSequenceEqual(
                    Contact.objects.filter(lookup).order_by("id"), contacts
                )

    def test_lte_subquery(self):
        with self.assertRaisesMessage(
            NotSupportedError, "'lte' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer__lte=subquery).order_by("id"), ()
            )

    def test_gt(self):
        test_cases = (
            (self.customer_1, (self.contact_3, self.contact_4, self.contact_6)),
            (self.customer_2, (self.contact_4, self.contact_6)),
            (self.customer_5, (self.contact_4,)),
            (self.customer_3, ()),
            (self.customer_4, ()),
        )

        for customer, contacts in test_cases:
            with self.subTest(
                "filter(customer__gt=customer)",
                customer=customer,
                contacts=contacts,
            ):
                self.assertSequenceEqual(
                    Contact.objects.filter(customer__gt=customer).order_by("id"),
                    contacts,
                )
            with self.subTest(
                "filter(TupleGreaterThan)",
                customer=customer,
                contacts=contacts,
            ):
                lhs = (F("customer_code"), F("company_code"))
                rhs = (customer.customer_id, customer.company)
                lookup = TupleGreaterThan(lhs, rhs)
                self.assertSequenceEqual(
                    Contact.objects.filter(lookup).order_by("id"), contacts
                )

    def test_gt_subquery(self):
        with self.assertRaisesMessage(
            NotSupportedError, "'gt' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer__gt=subquery).order_by("id"), ()
            )

    def test_gte(self):
        c1, c2, c3, c4, c5, c6 = (
            self.contact_1,
            self.contact_2,
            self.contact_3,
            self.contact_4,
            self.contact_5,
            self.contact_6,
        )
        test_cases = (
            (self.customer_1, (c1, c2, c3, c4, c5, c6)),
            (self.customer_2, (c3, c4, c6)),
            (self.customer_5, (c4, c6)),
            (self.customer_3, (c4,)),
            (self.customer_4, ()),
        )

        for customer, contacts in test_cases:
            with self.subTest(
                "filter(customer__gte=customer)",
                customer=customer,
                contacts=contacts,
            ):
                self.assertSequenceEqual(
                    Contact.objects.filter(customer__gte=customer).order_by("pk"),
                    contacts,
                )
            with self.subTest(
                "filter(TupleGreaterThanOrEqual)",
                customer=customer,
                contacts=contacts,
            ):
                lhs = (F("customer_code"), F("company_code"))
                rhs = (customer.customer_id, customer.company)
                lookup = TupleGreaterThanOrEqual(lhs, rhs)
                self.assertSequenceEqual(
                    Contact.objects.filter(lookup).order_by("id"), contacts
                )

    def test_gte_subquery(self):
        with self.assertRaisesMessage(
            NotSupportedError, "'gte' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer__gte=subquery).order_by("id"), ()
            )

    def test_isnull(self):
        contacts = (
            self.contact_1,
            self.contact_2,
            self.contact_3,
            self.contact_4,
            self.contact_5,
            self.contact_6,
        )

        with self.subTest("filter(customer__isnull=True)"):
            self.assertSequenceEqual(
                Contact.objects.filter(customer__isnull=True).order_by("id"),
                (),
            )
        with self.subTest("filter(TupleIsNull(True))"):
            lhs = (F("customer_code"), F("company_code"))
            lookup = TupleIsNull(lhs, True)
            self.assertSequenceEqual(
                Contact.objects.filter(lookup).order_by("id"),
                (),
            )
        with self.subTest("filter(customer__isnull=False)"):
            self.assertSequenceEqual(
                Contact.objects.filter(customer__isnull=False).order_by("id"),
                contacts,
            )
        with self.subTest("filter(TupleIsNull(False))"):
            lhs = (F("customer_code"), F("company_code"))
            lookup = TupleIsNull(lhs, False)
            self.assertSequenceEqual(
                Contact.objects.filter(lookup).order_by("id"),
                contacts,
            )

    def test_isnull_subquery(self):
        with self.assertRaisesMessage(
            NotSupportedError, "'isnull' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=0)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer__isnull=subquery).order_by("id"), ()
            )

    def test_lookup_errors(self):
        m_2_elements = "'%s' lookup of 'customer' field must have 2 elements"
        m_2_elements_each = "'in' lookup of 'customer' field must have 2 elements each"
        test_cases = (
            ({"customer": 1}, m_2_elements % "exact"),
            ({"customer": (1, 2, 3)}, m_2_elements % "exact"),
            ({"customer__in": (1, 2, 3)}, m_2_elements_each),
            ({"customer__in": ("foo", "bar")}, m_2_elements_each),
            ({"customer__gt": 1}, m_2_elements % "gt"),
            ({"customer__gt": (1, 2, 3)}, m_2_elements % "gt"),
            ({"customer__gte": 1}, m_2_elements % "gte"),
            ({"customer__gte": (1, 2, 3)}, m_2_elements % "gte"),
            ({"customer__lt": 1}, m_2_elements % "lt"),
            ({"customer__lt": (1, 2, 3)}, m_2_elements % "lt"),
            ({"customer__lte": 1}, m_2_elements % "lte"),
            ({"customer__lte": (1, 2, 3)}, m_2_elements % "lte"),
        )

        for kwargs, message in test_cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesMessage(ValueError, message),
            ):
                Contact.objects.get(**kwargs)

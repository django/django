import itertools

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
from django.db.models.lookups import In
from django.test import TestCase, skipUnlessDBFeature

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
        msg = (
            "The QuerySet value for the exact lookup must have 2 selected "
            "fields (received 1)"
        )
        with self.assertRaisesMessage(ValueError, msg):
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

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_in_subquery(self):
        subquery = Customer.objects.filter(id=self.customer_1.id)[:1]
        self.assertSequenceEqual(
            Contact.objects.filter(customer__in=subquery).order_by("id"),
            (self.contact_1, self.contact_2, self.contact_5),
        )

    def test_tuple_in_subquery_must_be_query(self):
        lhs = (F("customer_code"), F("company_code"))
        # If rhs is any non-Query object with an as_sql() function.
        rhs = In(F("customer_code"), [1, 2, 3])
        with self.assertRaisesMessage(
            ValueError,
            "'in' subquery lookup of ('customer_code', 'company_code') "
            "must be a Query object (received 'In')",
        ):
            TupleIn(lhs, rhs)

    def test_tuple_in_subquery_must_have_2_fields(self):
        lhs = (F("customer_code"), F("company_code"))
        rhs = Customer.objects.values_list("customer_id").query
        msg = (
            "The QuerySet value for the 'in' lookup must have 2 selected "
            "fields (received 1)"
        )
        with self.assertRaisesMessage(ValueError, msg):
            TupleIn(lhs, rhs)

    def test_tuple_in_subquery(self):
        customers = Customer.objects.values_list("customer_id", "company")
        test_cases = (
            (self.customer_1, (self.contact_1, self.contact_2, self.contact_5)),
            (self.customer_2, (self.contact_3,)),
            (self.customer_3, (self.contact_4,)),
            (self.customer_4, ()),
            (self.customer_5, (self.contact_6,)),
        )

        for customer, contacts in test_cases:
            lhs = (F("customer_code"), F("company_code"))
            rhs = customers.filter(id=customer.id).query
            lookup = TupleIn(lhs, rhs)
            qs = Contact.objects.filter(lookup).order_by("id")

            with self.subTest(customer=customer.id, query=str(qs.query)):
                self.assertSequenceEqual(qs, contacts)

    def test_tuple_in_rhs_must_be_collection_of_tuples_or_lists(self):
        test_cases = (
            (1, 2, 3),
            ((1, 2), (3, 4), None),
        )

        for rhs in test_cases:
            with self.subTest(rhs=rhs):
                with self.assertRaisesMessage(
                    ValueError,
                    "'in' lookup of ('customer_code', 'company_code') "
                    "must be a collection of tuples or lists",
                ):
                    TupleIn((F("customer_code"), F("company_code")), rhs)

    def test_tuple_in_rhs_must_have_2_elements_each(self):
        test_cases = (
            ((),),
            ((1,),),
            ((1, 2, 3),),
        )

        for rhs in test_cases:
            with self.subTest(rhs=rhs):
                with self.assertRaisesMessage(
                    ValueError,
                    "'in' lookup of ('customer_code', 'company_code') "
                    "must have 2 elements each",
                ):
                    TupleIn((F("customer_code"), F("company_code")), rhs)

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
            ValueError, "'lt' doesn't support multi-column subqueries."
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
            ValueError, "'lte' doesn't support multi-column subqueries."
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
            ValueError, "'gt' doesn't support multi-column subqueries."
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
            ValueError, "'gte' doesn't support multi-column subqueries."
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
            ValueError, "'isnull' doesn't support multi-column subqueries."
        ):
            subquery = Customer.objects.filter(id=0)[:1]
            self.assertSequenceEqual(
                Contact.objects.filter(customer__isnull=subquery).order_by("id"), ()
            )

    def test_lookup_errors(self):
        m_2_elements = "'%s' lookup of 'customer' must have 2 elements"
        m_2_elements_each = "'in' lookup of 'customer' must have 2 elements each"
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

    def test_tuple_lookup_names(self):
        test_cases = (
            (TupleExact, "exact"),
            (TupleGreaterThan, "gt"),
            (TupleGreaterThanOrEqual, "gte"),
            (TupleLessThan, "lt"),
            (TupleLessThanOrEqual, "lte"),
            (TupleIn, "in"),
            (TupleIsNull, "isnull"),
        )

        for lookup_class, lookup_name in test_cases:
            with self.subTest(lookup_name):
                self.assertEqual(lookup_class.lookup_name, lookup_name)

    def test_tuple_lookup_rhs_must_be_tuple_or_list(self):
        test_cases = itertools.product(
            (
                TupleExact,
                TupleGreaterThan,
                TupleGreaterThanOrEqual,
                TupleLessThan,
                TupleLessThanOrEqual,
                TupleIn,
            ),
            (
                0,
                1,
                None,
                True,
                False,
                {"foo": "bar"},
            ),
        )

        for lookup_cls, rhs in test_cases:
            lookup_name = lookup_cls.lookup_name
            with self.subTest(lookup_name=lookup_name, rhs=rhs):
                with self.assertRaisesMessage(
                    ValueError,
                    f"'{lookup_name}' lookup of ('customer_code', 'company_code') "
                    "must be a tuple or a list",
                ):
                    lookup_cls((F("customer_code"), F("company_code")), rhs)

    def test_tuple_lookup_rhs_must_have_2_elements(self):
        test_cases = itertools.product(
            (
                TupleExact,
                TupleGreaterThan,
                TupleGreaterThanOrEqual,
                TupleLessThan,
                TupleLessThanOrEqual,
            ),
            (
                [],
                [1],
                [1, 2, 3],
                (),
                (1,),
                (1, 2, 3),
            ),
        )

        for lookup_cls, rhs in test_cases:
            lookup_name = lookup_cls.lookup_name
            with self.subTest(lookup_name=lookup_name, rhs=rhs):
                with self.assertRaisesMessage(
                    ValueError,
                    f"'{lookup_name}' lookup of ('customer_code', 'company_code') "
                    "must have 2 elements",
                ):
                    lookup_cls((F("customer_code"), F("company_code")), rhs)

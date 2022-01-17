import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Order, RevisionableModel, TestObject


class ExtraRegressTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = User.objects.create_user(
            username="fred", password="secret", email="fred@example.com"
        )

    def test_regression_7314_7372(self):
        """
        Regression tests for #7314 and #7372
        """
        rm = RevisionableModel.objects.create(
            title="First Revision", when=datetime.datetime(2008, 9, 28, 10, 30, 0)
        )
        self.assertEqual(rm.pk, rm.base.pk)

        rm2 = rm.new_revision()
        rm2.title = "Second Revision"
        rm.when = datetime.datetime(2008, 9, 28, 14, 25, 0)
        rm2.save()

        self.assertEqual(rm2.title, "Second Revision")
        self.assertEqual(rm2.base.title, "First Revision")

        self.assertNotEqual(rm2.pk, rm.pk)
        self.assertEqual(rm2.base.pk, rm.pk)

        # Queryset to match most recent revision:
        qs = RevisionableModel.objects.extra(
            where=[
                "%(table)s.id IN "
                "(SELECT MAX(rev.id) FROM %(table)s rev GROUP BY rev.base_id)"
                % {
                    "table": RevisionableModel._meta.db_table,
                }
            ]
        )

        self.assertQuerysetEqual(
            qs,
            [("Second Revision", "First Revision")],
            transform=lambda r: (r.title, r.base.title),
        )

        # Queryset to search for string in title:
        qs2 = RevisionableModel.objects.filter(title__contains="Revision")
        self.assertQuerysetEqual(
            qs2,
            [
                ("First Revision", "First Revision"),
                ("Second Revision", "First Revision"),
            ],
            transform=lambda r: (r.title, r.base.title),
            ordered=False,
        )

        # Following queryset should return the most recent revision:
        self.assertQuerysetEqual(
            qs & qs2,
            [("Second Revision", "First Revision")],
            transform=lambda r: (r.title, r.base.title),
            ordered=False,
        )

    def test_extra_stay_tied(self):
        # Extra select parameters should stay tied to their corresponding
        # select portions. Applies when portions are updated or otherwise
        # moved around.
        qs = User.objects.extra(
            select={"alpha": "%s", "beta": "2", "gamma": "%s"}, select_params=(1, 3)
        )
        qs = qs.extra(select={"beta": 4})
        qs = qs.extra(select={"alpha": "%s"}, select_params=[5])
        self.assertEqual(
            list(qs.filter(id=self.u.id).values("alpha", "beta", "gamma")),
            [{"alpha": 5, "beta": 4, "gamma": 3}],
        )

    def test_regression_7957(self):
        """
        Regression test for #7957: Combining extra() calls should leave the
        corresponding parameters associated with the right extra() bit. I.e.
        internal dictionary must remain sorted.
        """
        self.assertEqual(
            (
                User.objects.extra(select={"alpha": "%s"}, select_params=(1,))
                .extra(select={"beta": "%s"}, select_params=(2,))[0]
                .alpha
            ),
            1,
        )

        self.assertEqual(
            (
                User.objects.extra(select={"beta": "%s"}, select_params=(1,))
                .extra(select={"alpha": "%s"}, select_params=(2,))[0]
                .alpha
            ),
            2,
        )

    def test_regression_7961(self):
        """
        Regression test for #7961: When not using a portion of an
        extra(...) in a query, remove any corresponding parameters from the
        query as well.
        """
        self.assertEqual(
            list(
                User.objects.extra(select={"alpha": "%s"}, select_params=(-6,))
                .filter(id=self.u.id)
                .values_list("id", flat=True)
            ),
            [self.u.id],
        )

    def test_regression_8063(self):
        """
        Regression test for #8063: limiting a query shouldn't discard any
        extra() bits.
        """
        qs = User.objects.extra(where=["id=%s"], params=[self.u.id])
        self.assertSequenceEqual(qs, [self.u])
        self.assertSequenceEqual(qs[:1], [self.u])

    def test_regression_8039(self):
        """
        Regression test for #8039: Ordering sometimes removed relevant tables
        from extra(). This test is the critical case: ordering uses a table,
        but then removes the reference because of an optimization. The table
        should still be present because of the extra() call.
        """
        self.assertQuerysetEqual(
            (
                Order.objects.extra(
                    where=["username=%s"], params=["fred"], tables=["auth_user"]
                ).order_by("created_by")
            ),
            [],
        )

    def test_regression_8819(self):
        """
        Regression test for #8819: Fields in the extra(select=...) list
        should be available to extra(order_by=...).
        """
        self.assertSequenceEqual(
            User.objects.filter(pk=self.u.id)
            .extra(select={"extra_field": 1})
            .distinct(),
            [self.u],
        )
        self.assertSequenceEqual(
            User.objects.filter(pk=self.u.id).extra(
                select={"extra_field": 1}, order_by=["extra_field"]
            ),
            [self.u],
        )
        self.assertSequenceEqual(
            User.objects.filter(pk=self.u.id)
            .extra(select={"extra_field": 1}, order_by=["extra_field"])
            .distinct(),
            [self.u],
        )

    def test_dates_query(self):
        """
        When calling the dates() method on a queryset with extra selection
        columns, we can (and should) ignore those columns. They don't change
        the result and cause incorrect SQL to be produced otherwise.
        """
        RevisionableModel.objects.create(
            title="First Revision", when=datetime.datetime(2008, 9, 28, 10, 30, 0)
        )

        self.assertSequenceEqual(
            RevisionableModel.objects.extra(select={"the_answer": "id"}).datetimes(
                "when", "month"
            ),
            [datetime.datetime(2008, 9, 1, 0, 0)],
        )

    def test_values_with_extra(self):
        """
        Regression test for #10256... If there is a values() clause, Extra
        columns are only returned if they are explicitly mentioned.
        """
        obj = TestObject(first="first", second="second", third="third")
        obj.save()

        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values()
            ),
            [
                {
                    "bar": "second",
                    "third": "third",
                    "second": "second",
                    "whiz": "third",
                    "foo": "first",
                    "id": obj.pk,
                    "first": "first",
                }
            ],
        )

        # Extra clauses after an empty values clause are still included
        self.assertEqual(
            list(
                TestObject.objects.values().extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                )
            ),
            [
                {
                    "bar": "second",
                    "third": "third",
                    "second": "second",
                    "whiz": "third",
                    "foo": "first",
                    "id": obj.pk,
                    "first": "first",
                }
            ],
        )

        # Extra columns are ignored if not mentioned in the values() clause
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values("first", "second")
            ),
            [{"second": "second", "first": "first"}],
        )

        # Extra columns after a non-empty values() clause are ignored
        self.assertEqual(
            list(
                TestObject.objects.values("first", "second").extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                )
            ),
            [{"second": "second", "first": "first"}],
        )

        # Extra columns can be partially returned
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values("first", "second", "foo")
            ),
            [{"second": "second", "foo": "first", "first": "first"}],
        )

        # Also works if only extra columns are included
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values("foo", "whiz")
            ),
            [{"foo": "first", "whiz": "third"}],
        )

        # Values list works the same way
        # All columns are returned for an empty values_list()
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list()
            ),
            [("first", "second", "third", obj.pk, "first", "second", "third")],
        )

        # Extra columns after an empty values_list() are still included
        self.assertEqual(
            list(
                TestObject.objects.values_list().extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                )
            ),
            [("first", "second", "third", obj.pk, "first", "second", "third")],
        )

        # Extra columns ignored completely if not mentioned in values_list()
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("first", "second")
            ),
            [("first", "second")],
        )

        # Extra columns after a non-empty values_list() clause are ignored completely
        self.assertEqual(
            list(
                TestObject.objects.values_list("first", "second").extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                )
            ),
            [("first", "second")],
        )

        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("second", flat=True)
            ),
            ["second"],
        )

        # Only the extra columns specified in the values_list() are returned
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("first", "second", "whiz")
            ),
            [("first", "second", "third")],
        )

        # ...also works if only extra columns are included
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("foo", "whiz")
            ),
            [("first", "third")],
        )

        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("whiz", flat=True)
            ),
            ["third"],
        )

        # ... and values are returned in the order they are specified
        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("whiz", "foo")
            ),
            [("third", "first")],
        )

        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("first", "id")
            ),
            [("first", obj.pk)],
        )

        self.assertEqual(
            list(
                TestObject.objects.extra(
                    select={"foo": "first", "bar": "second", "whiz": "third"}
                ).values_list("whiz", "first", "bar", "id")
            ),
            [("third", "first", "second", obj.pk)],
        )

    def test_regression_10847(self):
        """
        Regression for #10847: the list of extra columns can always be
        accurately evaluated. Using an inner query ensures that as_sql() is
        producing correct output without requiring full evaluation and
        execution of the inner query.
        """
        obj = TestObject(first="first", second="second", third="third")
        obj.save()

        self.assertEqual(
            list(TestObject.objects.extra(select={"extra": 1}).values("pk")),
            [{"pk": obj.pk}],
        )

        self.assertSequenceEqual(
            TestObject.objects.filter(
                pk__in=TestObject.objects.extra(select={"extra": 1}).values("pk")
            ),
            [obj],
        )

        self.assertEqual(
            list(TestObject.objects.values("pk").extra(select={"extra": 1})),
            [{"pk": obj.pk}],
        )

        self.assertSequenceEqual(
            TestObject.objects.filter(
                pk__in=TestObject.objects.values("pk").extra(select={"extra": 1})
            ),
            [obj],
        )

        self.assertSequenceEqual(
            TestObject.objects.filter(pk=obj.pk)
            | TestObject.objects.extra(where=["id > %s"], params=[obj.pk]),
            [obj],
        )

    def test_regression_17877(self):
        """
        Extra WHERE clauses get correctly ANDed, even when they
        contain OR operations.
        """
        # Test Case 1: should appear in queryset.
        t1 = TestObject.objects.create(first="a", second="a", third="a")
        # Test Case 2: should appear in queryset.
        t2 = TestObject.objects.create(first="b", second="a", third="a")
        # Test Case 3: should not appear in queryset, bug case.
        t = TestObject(first="a", second="a", third="b")
        t.save()
        # Test Case 4: should not appear in queryset.
        t = TestObject(first="b", second="a", third="b")
        t.save()
        # Test Case 5: should not appear in queryset.
        t = TestObject(first="b", second="b", third="a")
        t.save()
        # Test Case 6: should not appear in queryset, bug case.
        t = TestObject(first="a", second="b", third="b")
        t.save()

        self.assertCountEqual(
            TestObject.objects.extra(
                where=["first = 'a' OR second = 'a'", "third = 'a'"],
            ),
            [t1, t2],
        )

    def test_extra_values_distinct_ordering(self):
        t1 = TestObject.objects.create(first="a", second="a", third="a")
        t2 = TestObject.objects.create(first="a", second="b", third="b")
        qs = (
            TestObject.objects.extra(select={"second_extra": "second"})
            .values_list("id", flat=True)
            .distinct()
        )
        self.assertSequenceEqual(qs.order_by("second_extra"), [t1.pk, t2.pk])
        self.assertSequenceEqual(qs.order_by("-second_extra"), [t2.pk, t1.pk])
        # Note: the extra ordering must appear in select clause, so we get two
        # non-distinct results here (this is on purpose, see #7070).
        # Extra select doesn't appear in result values.
        self.assertSequenceEqual(
            qs.order_by("-second_extra").values_list("first"), [("a",), ("a",)]
        )

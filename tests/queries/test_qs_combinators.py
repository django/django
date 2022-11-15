import operator

from django.db import DatabaseError, NotSupportedError, connection
from django.db.models import Exists, F, IntegerField, OuterRef, Subquery, Value
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from .models import Author, Celebrity, ExtraInfo, Number, ReservedName


@skipUnlessDBFeature("supports_select_union")
class QuerySetSetOperationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Number.objects.bulk_create(Number(num=i, other_num=10 - i) for i in range(10))

    def assertNumbersEqual(self, queryset, expected_numbers, ordered=True):
        self.assertQuerySetEqual(
            queryset, expected_numbers, operator.attrgetter("num"), ordered
        )

    def test_simple_union(self):
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=8)
        qs3 = Number.objects.filter(num=5)
        self.assertNumbersEqual(qs1.union(qs2, qs3), [0, 1, 5, 8, 9], ordered=False)

    @skipUnlessDBFeature("supports_select_intersection")
    def test_simple_intersection(self):
        qs1 = Number.objects.filter(num__lte=5)
        qs2 = Number.objects.filter(num__gte=5)
        qs3 = Number.objects.filter(num__gte=4, num__lte=6)
        self.assertNumbersEqual(qs1.intersection(qs2, qs3), [5], ordered=False)

    @skipUnlessDBFeature("supports_select_intersection")
    def test_intersection_with_values(self):
        ReservedName.objects.create(name="a", order=2)
        qs1 = ReservedName.objects.all()
        reserved_name = qs1.intersection(qs1).values("name", "order", "id").get()
        self.assertEqual(reserved_name["name"], "a")
        self.assertEqual(reserved_name["order"], 2)
        reserved_name = qs1.intersection(qs1).values_list("name", "order", "id").get()
        self.assertEqual(reserved_name[:2], ("a", 2))

    @skipUnlessDBFeature("supports_select_difference")
    def test_simple_difference(self):
        qs1 = Number.objects.filter(num__lte=5)
        qs2 = Number.objects.filter(num__lte=4)
        self.assertNumbersEqual(qs1.difference(qs2), [5], ordered=False)

    def test_union_distinct(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        self.assertEqual(len(list(qs1.union(qs2, all=True))), 20)
        self.assertEqual(len(list(qs1.union(qs2))), 10)

    def test_union_none(self):
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=8)
        qs3 = qs1.union(qs2)
        self.assertSequenceEqual(qs3.none(), [])
        self.assertNumbersEqual(qs3, [0, 1, 8, 9], ordered=False)

    def test_union_none_slice(self):
        qs1 = Number.objects.filter(num__lte=0)
        qs2 = Number.objects.none()
        qs3 = qs1.union(qs2)
        self.assertNumbersEqual(qs3[:1], [0])

    def test_union_empty_filter_slice(self):
        qs1 = Number.objects.filter(num__lte=0)
        qs2 = Number.objects.filter(pk__in=[])
        qs3 = qs1.union(qs2)
        self.assertNumbersEqual(qs3[:1], [0])

    @skipUnlessDBFeature("supports_slicing_ordering_in_compound")
    def test_union_slice_compound_empty(self):
        qs1 = Number.objects.filter(num__lte=0)[:1]
        qs2 = Number.objects.none()
        qs3 = qs1.union(qs2)
        self.assertNumbersEqual(qs3[:1], [0])

    @skipUnlessDBFeature("supports_slicing_ordering_in_compound")
    def test_union_combined_slice_compound_empty(self):
        qs1 = Number.objects.filter(num__lte=2)[:3]
        qs2 = Number.objects.none()
        qs3 = qs1.union(qs2)
        self.assertNumbersEqual(qs3.order_by("num")[2:3], [2])

    def test_union_order_with_null_first_last(self):
        Number.objects.filter(other_num=5).update(other_num=None)
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=2)
        qs3 = qs1.union(qs2)
        self.assertSequenceEqual(
            qs3.order_by(
                F("other_num").asc(nulls_first=True),
            ).values_list("other_num", flat=True),
            [None, 1, 2, 3, 4, 6, 7, 8, 9, 10],
        )
        self.assertSequenceEqual(
            qs3.order_by(
                F("other_num").asc(nulls_last=True),
            ).values_list("other_num", flat=True),
            [1, 2, 3, 4, 6, 7, 8, 9, 10, None],
        )

    @skipUnlessDBFeature("supports_select_intersection")
    def test_intersection_with_empty_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.none()
        qs3 = Number.objects.filter(pk__in=[])
        self.assertEqual(len(qs1.intersection(qs2)), 0)
        self.assertEqual(len(qs1.intersection(qs3)), 0)
        self.assertEqual(len(qs2.intersection(qs1)), 0)
        self.assertEqual(len(qs3.intersection(qs1)), 0)
        self.assertEqual(len(qs2.intersection(qs2)), 0)
        self.assertEqual(len(qs3.intersection(qs3)), 0)

    @skipUnlessDBFeature("supports_select_difference")
    def test_difference_with_empty_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.none()
        qs3 = Number.objects.filter(pk__in=[])
        self.assertEqual(len(qs1.difference(qs2)), 10)
        self.assertEqual(len(qs1.difference(qs3)), 10)
        self.assertEqual(len(qs2.difference(qs1)), 0)
        self.assertEqual(len(qs3.difference(qs1)), 0)
        self.assertEqual(len(qs2.difference(qs2)), 0)
        self.assertEqual(len(qs3.difference(qs3)), 0)

    @skipUnlessDBFeature("supports_select_difference")
    def test_difference_with_values(self):
        ReservedName.objects.create(name="a", order=2)
        qs1 = ReservedName.objects.all()
        qs2 = ReservedName.objects.none()
        reserved_name = qs1.difference(qs2).values("name", "order", "id").get()
        self.assertEqual(reserved_name["name"], "a")
        self.assertEqual(reserved_name["order"], 2)
        reserved_name = qs1.difference(qs2).values_list("name", "order", "id").get()
        self.assertEqual(reserved_name[:2], ("a", 2))

    def test_union_with_empty_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.none()
        qs3 = Number.objects.filter(pk__in=[])
        self.assertEqual(len(qs1.union(qs2)), 10)
        self.assertEqual(len(qs2.union(qs1)), 10)
        self.assertEqual(len(qs1.union(qs3)), 10)
        self.assertEqual(len(qs3.union(qs1)), 10)
        self.assertEqual(len(qs2.union(qs1, qs1, qs1)), 10)
        self.assertEqual(len(qs2.union(qs1, qs1, all=True)), 20)
        self.assertEqual(len(qs2.union(qs2)), 0)
        self.assertEqual(len(qs3.union(qs3)), 0)

    def test_empty_qs_union_with_ordered_qs(self):
        qs1 = Number.objects.order_by("num")
        qs2 = Number.objects.none().union(qs1).order_by("num")
        self.assertEqual(list(qs1), list(qs2))

    def test_limits(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        self.assertEqual(len(list(qs1.union(qs2)[:2])), 2)

    def test_ordering(self):
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=2, num__lte=3)
        self.assertNumbersEqual(qs1.union(qs2).order_by("-num"), [3, 2, 1, 0])

    def test_ordering_by_alias(self):
        qs1 = Number.objects.filter(num__lte=1).values(alias=F("num"))
        qs2 = Number.objects.filter(num__gte=2, num__lte=3).values(alias=F("num"))
        self.assertQuerySetEqual(
            qs1.union(qs2).order_by("-alias"),
            [3, 2, 1, 0],
            operator.itemgetter("alias"),
        )

    def test_ordering_by_f_expression(self):
        qs1 = Number.objects.filter(num__lte=1)
        qs2 = Number.objects.filter(num__gte=2, num__lte=3)
        self.assertNumbersEqual(qs1.union(qs2).order_by(F("num").desc()), [3, 2, 1, 0])

    def test_ordering_by_f_expression_and_alias(self):
        qs1 = Number.objects.filter(num__lte=1).values(alias=F("other_num"))
        qs2 = Number.objects.filter(num__gte=2, num__lte=3).values(alias=F("other_num"))
        self.assertQuerySetEqual(
            qs1.union(qs2).order_by(F("alias").desc()),
            [10, 9, 8, 7],
            operator.itemgetter("alias"),
        )
        Number.objects.create(num=-1)
        self.assertQuerySetEqual(
            qs1.union(qs2).order_by(F("alias").desc(nulls_last=True)),
            [10, 9, 8, 7, None],
            operator.itemgetter("alias"),
        )

    def test_union_with_values(self):
        ReservedName.objects.create(name="a", order=2)
        qs1 = ReservedName.objects.all()
        reserved_name = qs1.union(qs1).values("name", "order", "id").get()
        self.assertEqual(reserved_name["name"], "a")
        self.assertEqual(reserved_name["order"], 2)
        reserved_name = qs1.union(qs1).values_list("name", "order", "id").get()
        self.assertEqual(reserved_name[:2], ("a", 2))
        # List of columns can be changed.
        reserved_name = qs1.union(qs1).values_list("order").get()
        self.assertEqual(reserved_name, (2,))

    def test_union_with_two_annotated_values_list(self):
        qs1 = (
            Number.objects.filter(num=1)
            .annotate(
                count=Value(0, IntegerField()),
            )
            .values_list("num", "count")
        )
        qs2 = (
            Number.objects.filter(num=2)
            .values("pk")
            .annotate(
                count=F("num"),
            )
            .annotate(
                num=Value(1, IntegerField()),
            )
            .values_list("num", "count")
        )
        self.assertCountEqual(qs1.union(qs2), [(1, 0), (2, 1)])

    def test_union_with_extra_and_values_list(self):
        qs1 = (
            Number.objects.filter(num=1)
            .extra(
                select={"count": 0},
            )
            .values_list("num", "count")
        )
        qs2 = Number.objects.filter(num=2).extra(select={"count": 1})
        self.assertCountEqual(qs1.union(qs2), [(1, 0), (2, 1)])

    def test_union_with_values_list_on_annotated_and_unannotated(self):
        ReservedName.objects.create(name="rn1", order=1)
        qs1 = Number.objects.annotate(
            has_reserved_name=Exists(ReservedName.objects.filter(order=OuterRef("num")))
        ).filter(has_reserved_name=True)
        qs2 = Number.objects.filter(num=9)
        self.assertCountEqual(qs1.union(qs2).values_list("num", flat=True), [1, 9])

    def test_union_with_values_list_and_order(self):
        ReservedName.objects.bulk_create(
            [
                ReservedName(name="rn1", order=7),
                ReservedName(name="rn2", order=5),
                ReservedName(name="rn0", order=6),
                ReservedName(name="rn9", order=-1),
            ]
        )
        qs1 = ReservedName.objects.filter(order__gte=6)
        qs2 = ReservedName.objects.filter(order__lte=5)
        union_qs = qs1.union(qs2)
        for qs, expected_result in (
            # Order by a single column.
            (union_qs.order_by("-pk").values_list("order", flat=True), [-1, 6, 5, 7]),
            (union_qs.order_by("pk").values_list("order", flat=True), [7, 5, 6, -1]),
            (union_qs.values_list("order", flat=True).order_by("-pk"), [-1, 6, 5, 7]),
            (union_qs.values_list("order", flat=True).order_by("pk"), [7, 5, 6, -1]),
            # Order by multiple columns.
            (
                union_qs.order_by("-name", "pk").values_list("order", flat=True),
                [-1, 5, 7, 6],
            ),
            (
                union_qs.values_list("order", flat=True).order_by("-name", "pk"),
                [-1, 5, 7, 6],
            ),
        ):
            with self.subTest(qs=qs):
                self.assertEqual(list(qs), expected_result)

    def test_union_with_values_list_and_order_on_annotation(self):
        qs1 = Number.objects.annotate(
            annotation=Value(-1),
            multiplier=F("annotation"),
        ).filter(num__gte=6)
        qs2 = Number.objects.annotate(
            annotation=Value(2),
            multiplier=F("annotation"),
        ).filter(num__lte=5)
        self.assertSequenceEqual(
            qs1.union(qs2).order_by("annotation", "num").values_list("num", flat=True),
            [6, 7, 8, 9, 0, 1, 2, 3, 4, 5],
        )
        self.assertQuerySetEqual(
            qs1.union(qs2)
            .order_by(
                F("annotation") * F("multiplier"),
                "num",
            )
            .values("num"),
            [6, 7, 8, 9, 0, 1, 2, 3, 4, 5],
            operator.itemgetter("num"),
        )

    def test_union_with_select_related_and_order(self):
        e1 = ExtraInfo.objects.create(value=7, info="e1")
        a1 = Author.objects.create(name="a1", num=1, extra=e1)
        a2 = Author.objects.create(name="a2", num=3, extra=e1)
        Author.objects.create(name="a3", num=2, extra=e1)
        base_qs = Author.objects.select_related("extra").order_by()
        qs1 = base_qs.filter(name="a1")
        qs2 = base_qs.filter(name="a2")
        self.assertSequenceEqual(qs1.union(qs2).order_by("pk"), [a1, a2])

    @skipUnlessDBFeature("supports_slicing_ordering_in_compound")
    def test_union_with_select_related_and_first(self):
        e1 = ExtraInfo.objects.create(value=7, info="e1")
        a1 = Author.objects.create(name="a1", num=1, extra=e1)
        Author.objects.create(name="a2", num=3, extra=e1)
        base_qs = Author.objects.select_related("extra")
        qs1 = base_qs.filter(name="a1")
        qs2 = base_qs.filter(name="a2")
        self.assertEqual(qs1.union(qs2).first(), a1)

    def test_union_with_first(self):
        e1 = ExtraInfo.objects.create(value=7, info="e1")
        a1 = Author.objects.create(name="a1", num=1, extra=e1)
        base_qs = Author.objects.order_by()
        qs1 = base_qs.filter(name="a1")
        qs2 = base_qs.filter(name="a2")
        self.assertEqual(qs1.union(qs2).first(), a1)

    def test_union_multiple_models_with_values_list_and_order(self):
        reserved_name = ReservedName.objects.create(name="rn1", order=0)
        qs1 = Celebrity.objects.all()
        qs2 = ReservedName.objects.all()
        self.assertSequenceEqual(
            qs1.union(qs2).order_by("name").values_list("pk", flat=True),
            [reserved_name.pk],
        )

    def test_union_multiple_models_with_values_list_and_order_by_extra_select(self):
        reserved_name = ReservedName.objects.create(name="rn1", order=0)
        qs1 = Celebrity.objects.extra(select={"extra_name": "name"})
        qs2 = ReservedName.objects.extra(select={"extra_name": "name"})
        self.assertSequenceEqual(
            qs1.union(qs2).order_by("extra_name").values_list("pk", flat=True),
            [reserved_name.pk],
        )

    def test_union_in_subquery(self):
        ReservedName.objects.bulk_create(
            [
                ReservedName(name="rn1", order=8),
                ReservedName(name="rn2", order=1),
                ReservedName(name="rn3", order=5),
            ]
        )
        qs1 = Number.objects.filter(num__gt=7, num=OuterRef("order"))
        qs2 = Number.objects.filter(num__lt=2, num=OuterRef("order"))
        self.assertCountEqual(
            ReservedName.objects.annotate(
                number=Subquery(qs1.union(qs2).values("num")),
            )
            .filter(number__isnull=False)
            .values_list("order", flat=True),
            [8, 1],
        )

    def test_union_in_subquery_related_outerref(self):
        e1 = ExtraInfo.objects.create(value=7, info="e3")
        e2 = ExtraInfo.objects.create(value=5, info="e2")
        e3 = ExtraInfo.objects.create(value=1, info="e1")
        Author.objects.bulk_create(
            [
                Author(name="a1", num=1, extra=e1),
                Author(name="a2", num=3, extra=e2),
                Author(name="a3", num=2, extra=e3),
            ]
        )
        qs1 = ExtraInfo.objects.order_by().filter(value=OuterRef("num"))
        qs2 = ExtraInfo.objects.order_by().filter(value__lt=OuterRef("extra__value"))
        qs = (
            Author.objects.annotate(
                info=Subquery(qs1.union(qs2).values("info")[:1]),
            )
            .filter(info__isnull=False)
            .values_list("name", flat=True)
        )
        self.assertCountEqual(qs, ["a1", "a2"])
        # Combined queries don't mutate.
        self.assertCountEqual(qs, ["a1", "a2"])

    @skipUnlessDBFeature("supports_slicing_ordering_in_compound")
    def test_union_in_with_ordering(self):
        qs1 = Number.objects.filter(num__gt=7).order_by("num")
        qs2 = Number.objects.filter(num__lt=2).order_by("num")
        self.assertNumbersEqual(
            Number.objects.exclude(id__in=qs1.union(qs2).values("id")),
            [2, 3, 4, 5, 6, 7],
            ordered=False,
        )

    @skipUnlessDBFeature(
        "supports_slicing_ordering_in_compound", "allow_sliced_subqueries_with_in"
    )
    def test_union_in_with_ordering_and_slice(self):
        qs1 = Number.objects.filter(num__gt=7).order_by("num")[:1]
        qs2 = Number.objects.filter(num__lt=2).order_by("-num")[:1]
        self.assertNumbersEqual(
            Number.objects.exclude(id__in=qs1.union(qs2).values("id")),
            [0, 2, 3, 4, 5, 6, 7, 9],
            ordered=False,
        )

    def test_count_union(self):
        qs1 = Number.objects.filter(num__lte=1).values("num")
        qs2 = Number.objects.filter(num__gte=2, num__lte=3).values("num")
        self.assertEqual(qs1.union(qs2).count(), 4)

    def test_count_union_empty_result(self):
        qs = Number.objects.filter(pk__in=[])
        self.assertEqual(qs.union(qs).count(), 0)

    @skipUnlessDBFeature("supports_select_difference")
    def test_count_difference(self):
        qs1 = Number.objects.filter(num__lt=10)
        qs2 = Number.objects.filter(num__lt=9)
        self.assertEqual(qs1.difference(qs2).count(), 1)

    @skipUnlessDBFeature("supports_select_intersection")
    def test_count_intersection(self):
        qs1 = Number.objects.filter(num__gte=5)
        qs2 = Number.objects.filter(num__lte=5)
        self.assertEqual(qs1.intersection(qs2).count(), 1)

    def test_exists_union(self):
        qs1 = Number.objects.filter(num__gte=5)
        qs2 = Number.objects.filter(num__lte=5)
        with CaptureQueriesContext(connection) as context:
            self.assertIs(qs1.union(qs2).exists(), True)
        captured_queries = context.captured_queries
        self.assertEqual(len(captured_queries), 1)
        captured_sql = captured_queries[0]["sql"]
        self.assertNotIn(
            connection.ops.quote_name(Number._meta.pk.column),
            captured_sql,
        )
        self.assertEqual(
            captured_sql.count(connection.ops.limit_offset_sql(None, 1)),
            3 if connection.features.supports_slicing_ordering_in_compound else 1,
        )

    def test_exists_union_empty_result(self):
        qs = Number.objects.filter(pk__in=[])
        self.assertIs(qs.union(qs).exists(), False)

    @skipUnlessDBFeature("supports_select_intersection")
    def test_exists_intersection(self):
        qs1 = Number.objects.filter(num__gt=5)
        qs2 = Number.objects.filter(num__lt=5)
        self.assertIs(qs1.intersection(qs1).exists(), True)
        self.assertIs(qs1.intersection(qs2).exists(), False)

    @skipUnlessDBFeature("supports_select_difference")
    def test_exists_difference(self):
        qs1 = Number.objects.filter(num__gte=5)
        qs2 = Number.objects.filter(num__gte=3)
        self.assertIs(qs1.difference(qs2).exists(), False)
        self.assertIs(qs2.difference(qs1).exists(), True)

    def test_get_union(self):
        qs = Number.objects.filter(num=2)
        self.assertEqual(qs.union(qs).get().num, 2)

    @skipUnlessDBFeature("supports_select_difference")
    def test_get_difference(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.exclude(num=2)
        self.assertEqual(qs1.difference(qs2).get().num, 2)

    @skipUnlessDBFeature("supports_select_intersection")
    def test_get_intersection(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.filter(num=2)
        self.assertEqual(qs1.intersection(qs2).get().num, 2)

    @skipUnlessDBFeature("supports_slicing_ordering_in_compound")
    def test_ordering_subqueries(self):
        qs1 = Number.objects.order_by("num")[:2]
        qs2 = Number.objects.order_by("-num")[:2]
        self.assertNumbersEqual(qs1.union(qs2).order_by("-num")[:4], [9, 8, 1, 0])

    @skipIfDBFeature("supports_slicing_ordering_in_compound")
    def test_unsupported_ordering_slicing_raises_db_error(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        qs3 = Number.objects.all()
        msg = "LIMIT/OFFSET not allowed in subqueries of compound statements"
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2[:10]))
        msg = "ORDER BY not allowed in subqueries of compound statements"
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.order_by("id").union(qs2))
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by("id").union(qs3))

    @skipIfDBFeature("supports_select_intersection")
    def test_unsupported_intersection_raises_db_error(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.all()
        msg = "intersection is not supported on this database backend"
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(qs1.intersection(qs2))

    def test_combining_multiple_models(self):
        ReservedName.objects.create(name="99 little bugs", order=99)
        qs1 = Number.objects.filter(num=1).values_list("num", flat=True)
        qs2 = ReservedName.objects.values_list("order")
        self.assertEqual(list(qs1.union(qs2).order_by("num")), [1, 99])

    def test_order_raises_on_non_selected_column(self):
        qs1 = (
            Number.objects.filter()
            .annotate(
                annotation=Value(1, IntegerField()),
            )
            .values("annotation", num2=F("num"))
        )
        qs2 = Number.objects.filter().values("id", "num")
        # Should not raise
        list(qs1.union(qs2).order_by("annotation"))
        list(qs1.union(qs2).order_by("num2"))
        msg = "ORDER BY term does not match any column in the result set"
        # 'id' is not part of the select
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by("id"))
        # 'num' got realiased to num2
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by("num"))
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by(F("num")))
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2).order_by(F("num").desc()))
        # switched order, now 'exists' again:
        list(qs2.union(qs1).order_by("num"))

    @skipUnlessDBFeature("supports_select_difference", "supports_select_intersection")
    def test_qs_with_subcompound_qs(self):
        qs1 = Number.objects.all()
        qs2 = Number.objects.intersection(Number.objects.filter(num__gt=1))
        self.assertEqual(qs1.difference(qs2).count(), 2)

    def test_order_by_same_type(self):
        qs = Number.objects.all()
        union = qs.union(qs)
        numbers = list(range(10))
        self.assertNumbersEqual(union.order_by("num"), numbers)
        self.assertNumbersEqual(union.order_by("other_num"), reversed(numbers))

    def test_unsupported_operations_on_combined_qs(self):
        qs = Number.objects.all()
        msg = "Calling QuerySet.%s() after %s() is not supported."
        combinators = ["union"]
        if connection.features.supports_select_difference:
            combinators.append("difference")
        if connection.features.supports_select_intersection:
            combinators.append("intersection")
        for combinator in combinators:
            for operation in (
                "alias",
                "annotate",
                "defer",
                "delete",
                "distinct",
                "exclude",
                "extra",
                "filter",
                "only",
                "prefetch_related",
                "select_related",
                "update",
            ):
                with self.subTest(combinator=combinator, operation=operation):
                    with self.assertRaisesMessage(
                        NotSupportedError,
                        msg % (operation, combinator),
                    ):
                        getattr(getattr(qs, combinator)(qs), operation)()
            with self.assertRaisesMessage(
                NotSupportedError,
                msg % ("contains", combinator),
            ):
                obj = Number.objects.first()
                getattr(qs, combinator)(qs).contains(obj)

    def test_get_with_filters_unsupported_on_combined_qs(self):
        qs = Number.objects.all()
        msg = "Calling QuerySet.get(...) with filters after %s() is not supported."
        combinators = ["union"]
        if connection.features.supports_select_difference:
            combinators.append("difference")
        if connection.features.supports_select_intersection:
            combinators.append("intersection")
        for combinator in combinators:
            with self.subTest(combinator=combinator):
                with self.assertRaisesMessage(NotSupportedError, msg % combinator):
                    getattr(qs, combinator)(qs).get(num=2)

    def test_operator_on_combined_qs_error(self):
        qs = Number.objects.all()
        msg = "Cannot use %s operator with combined queryset."
        combinators = ["union"]
        if connection.features.supports_select_difference:
            combinators.append("difference")
        if connection.features.supports_select_intersection:
            combinators.append("intersection")
        operators = [
            ("|", operator.or_),
            ("&", operator.and_),
            ("^", operator.xor),
        ]
        for combinator in combinators:
            combined_qs = getattr(qs, combinator)(qs)
            for operator_, operator_func in operators:
                with self.subTest(combinator=combinator):
                    with self.assertRaisesMessage(TypeError, msg % operator_):
                        operator_func(qs, combined_qs)
                    with self.assertRaisesMessage(TypeError, msg % operator_):
                        operator_func(combined_qs, qs)

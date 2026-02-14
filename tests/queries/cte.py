from unittest import skipUnless

from django.db.models import (
    Avg,
    BooleanField,
    CTE as DjangoCTE,
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Subquery,
    Value,
    When,
    with_cte as django_with_cte,
)
from django.db.models.functions import Cast, Coalesce, Concat, Length, Lower, Substr, Upper
from django.test import TestCase

from .models import NamedCategory, Tag

try:
    from django_cte import CTE as ExternalCTE
    from django_cte import with_cte as external_with_cte
except ImportError:
    HAS_DJANGO_CTE = False
    ExternalCTE = None
    external_with_cte = None
else:
    HAS_DJANGO_CTE = True

LIMIT_SELECT_BENCH = 20


class BenchmarkQueryMixin:
    @staticmethod
    def sq_children_count():
        return Subquery(
            Tag.objects.filter(parent_id=OuterRef("pk"))
            .values("parent_id")
            .annotate(c=Count("*"))
            .values("c")[:1],
            output_field=IntegerField(),
        )

    @staticmethod
    def sq_category_tag_count():
        return Subquery(
            Tag.objects.filter(category_id=OuterRef("category_id"))
            .values("category_id")
            .annotate(c=Count("*"))
            .values("c")[:1],
            output_field=IntegerField(),
        )

    @staticmethod
    def sq_latest_child_name():
        return Subquery(
            Tag.objects.filter(parent_id=OuterRef("pk")).order_by("-id").values("name")[:1]
        )

    @staticmethod
    def ex_has_children():
        return Exists(Tag.objects.filter(parent_id=OuterRef("pk")))

    @staticmethod
    def ex_has_sibling_same_category():
        return Exists(
            Tag.objects.filter(category_id=OuterRef("category_id")).exclude(pk=OuterRef("pk"))
        )

    @staticmethod
    def q0_no_annotations():
        return (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .order_by("category_id", "name", "id")
            .values("id", "name", "parent__name", "category__name")[:LIMIT_SELECT_BENCH]
        )

    def q1_nonduplicated_annotations(self):
        children_cnt = self.sq_children_count()
        cat_cnt = self.sq_category_tag_count()
        latest_child = self.sq_latest_child_name()

        return (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(
                name_upper=Upper(F("name")),
                name_lower=Lower(F("name")),
                name_len=Length(F("name")),
                name_prefix_3=Substr(F("name"), 1, 3),
                name_suffix_3=Substr(F("name"), Length(F("name")) - 2, 3),
                children_count=Coalesce(children_cnt, Value(0), output_field=IntegerField()),
                category_tag_count=Coalesce(cat_cnt, Value(0), output_field=IntegerField()),
                latest_child_name=Coalesce(latest_child, Value("")),
                has_children=Case(
                    When(self.ex_has_children(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                has_sibling_same_category=Case(
                    When(self.ex_has_sibling_same_category(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                score=(
                    Coalesce(children_cnt, Value(0)) * Value(10)
                    + Coalesce(cat_cnt, Value(0)) * Value(1)
                    + Cast(Length(F("name")), IntegerField())
                ),
                name_twice=Concat(F("name"), Value(" "), F("name")),
                name_thrice=Concat(F("name"), Value(" "), F("name"), Value(" "), F("name")),
            )
            .filter(category_tag_count__gte=2)
            .order_by("-children_count", "name", "id")
            .values(
                "id",
                "name",
                "parent__name",
                "category__name",
                "name_twice",
                "name_thrice",
                "name_upper",
                "name_lower",
                "name_len",
                "name_prefix_3",
                "name_suffix_3",
                "children_count",
                "category_tag_count",
                "latest_child_name",
                "has_children",
                "has_sibling_same_category",
                "score",
            )[:LIMIT_SELECT_BENCH]
        )

    def q2_duplicated_annotations(self):
        qs = (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(
                name_twice=Concat(F("name"), Value(" "), F("name")),
                name_upper=Upper(F("name")),
                children_count=Coalesce(self.sq_children_count(), Value(0), output_field=IntegerField()),
                category_tag_count=Coalesce(
                    self.sq_category_tag_count(), Value(0), output_field=IntegerField()
                ),
            )
        )
        qs = qs.annotate(
            name_twice_twice=Concat(F("name_twice"), Value(" "), F("name_twice")),
            name_upper_twice=Concat(F("name_upper"), Value("_"), F("name_upper")),
            score=F("children_count") * Value(10)
            + F("category_tag_count")
            + Cast(Length(F("name")), IntegerField()),
        )
        return (
            qs.filter(category_tag_count__gte=2)
            .order_by("-children_count", "name", "id")
            .values(
                "id",
                "name",
                "parent__name",
                "category__name",
                "name_twice",
                "name_twice_twice",
                "name_upper",
                "name_upper_twice",
                "children_count",
                "category_tag_count",
                "score",
            )[:LIMIT_SELECT_BENCH]
        )

    def q3_parent_category_via_subquery(self):
        parent_name_sq = Subquery(Tag.objects.filter(pk=OuterRef("parent_id")).values("name")[:1])
        category_name_sq = Subquery(
            NamedCategory.objects.filter(pk=OuterRef("category_id")).values("name")[:1]
        )

        return (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(
                parent_name_sq=Coalesce(parent_name_sq, Value("")),
                category_name_sq=Coalesce(category_name_sq, Value("")),
                has_children=Case(
                    When(self.ex_has_children(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .filter(has_children=True)
            .order_by("category_id", "name", "id")
            .values("id", "name", "parent_name_sq", "category_name_sq", "has_children")[
                :LIMIT_SELECT_BENCH
            ]
        )

    @staticmethod
    def q4_deep_duplication_chain(depth=6):
        qs = (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(a0=Concat(F("name"), Value(" "), F("name")))
        )
        for i in range(1, depth + 1):
            qs = qs.annotate(**{f"a{i}": Concat(F(f"a{i - 1}"), Value(" "), F(f"a{i - 1}"))})

        fields = ["id", "name", "parent__name", "category__name"] + [f"a{i}" for i in range(0, depth + 1)]
        return qs.order_by("id").values(*fields)[:LIMIT_SELECT_BENCH]

    @staticmethod
    def q5_plain_correlated_preagg_equivalent():
        children_cnt = Subquery(
            Tag.objects.filter(parent_id=OuterRef("pk"))
            .values("parent_id")
            .annotate(c=Count("*"))
            .values("c")[:1],
            output_field=IntegerField(),
        )
        category_cnt = Subquery(
            Tag.objects.filter(category_id=OuterRef("category_id"))
            .values("category_id")
            .annotate(c=Count("*"))
            .values("c")[:1],
            output_field=IntegerField(),
        )
        return (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(
                children_count=Coalesce(children_cnt, Value(0), output_field=IntegerField()),
                category_tag_count=Coalesce(category_cnt, Value(0), output_field=IntegerField()),
                score=F("children_count") * Value(10)
                + F("category_tag_count")
                + Cast(Length(F("name")), IntegerField()),
                score2=F("children_count") * Value(3) + F("category_tag_count") * Value(7),
                name_twice=Concat(F("name"), Value(" "), F("name")),
            )
            .filter(category_tag_count__gte=2)
            .order_by("-children_count", "name", "id")
            .values(
                "id",
                "name",
                "parent__name",
                "category__name",
                "children_count",
                "category_tag_count",
                "score",
                "score2",
                "name_twice",
            )[:LIMIT_SELECT_BENCH]
        )

    @staticmethod
    def q6_plain_correlated_minmaxavg_equivalent():
        cat_min_id = Subquery(
            Tag.objects.filter(category_id=OuterRef("category_id"))
            .values("category_id")
            .annotate(v=Min("id"))
            .values("v")[:1],
            output_field=IntegerField(),
        )
        cat_max_id = Subquery(
            Tag.objects.filter(category_id=OuterRef("category_id"))
            .values("category_id")
            .annotate(v=Max("id"))
            .values("v")[:1],
            output_field=IntegerField(),
        )
        cat_avg_name_len = Subquery(
            Tag.objects.filter(category_id=OuterRef("category_id"))
            .values("category_id")
            .annotate(v=Avg(Length("name")))
            .values("v")[:1]
        )

        return (
            Tag.objects.all()
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(
                category_min_id=Coalesce(cat_min_id, Value(0), output_field=IntegerField()),
                category_max_id=Coalesce(cat_max_id, Value(0), output_field=IntegerField()),
                category_avg_name_len=Coalesce(cat_avg_name_len, Value(0.0)),
                span=F("category_max_id") - F("category_min_id"),
                is_near_min=Case(
                    When(id__lte=F("category_min_id") + Value(50), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                name_twice=Concat("name", Value(" "), "name"),
                score=(F("id") - F("category_min_id"))
                + Cast(F("category_avg_name_len"), IntegerField()) * Value(10),
            )
            .filter(category_max_id__gt=F("category_min_id"))
            .filter(category_avg_name_len__gte=Value(6.0))
            .order_by("-span", "-score", "name", "id")
            .values(
                "id",
                "name",
                "parent__name",
                "category__name",
                "category_min_id",
                "category_max_id",
                "category_avg_name_len",
                "span",
                "is_near_min",
                "name_twice",
                "score",
            )[:LIMIT_SELECT_BENCH]
        )

    @staticmethod
    def _q6_explicit_cte(cte_cls, with_cte_fn):
        cte = cte_cls(
            Tag.objects.values("category_id").annotate(
                min_id=Min("id"),
                max_id=Max("id"),
                avg_len=Avg(Length("name")),
            )
        )
        return with_cte_fn(
            cte,
            select=cte.join(Tag.objects.all(), category_id=cte.col.category_id)
            .filter(category__isnull=False)
            .exclude(name="")
            .annotate(
                category_min_id=Coalesce(cte.col.min_id, Value(0), output_field=IntegerField()),
                category_max_id=Coalesce(cte.col.max_id, Value(0), output_field=IntegerField()),
                category_avg_name_len=Coalesce(cte.col.avg_len, Value(0.0)),
                span=cte.col.max_id - cte.col.min_id,
                is_near_min=Case(
                    When(id__lte=cte.col.min_id + Value(50), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                name_twice=Concat("name", Value(" "), "name"),
                score=(F("id") - cte.col.min_id)
                + Cast(cte.col.avg_len, IntegerField()) * Value(10),
            )
            .filter(category_max_id__gt=F("category_min_id"))
            .filter(category_avg_name_len__gte=Value(6.0))
            .order_by("-span", "-score", "name", "id")
            .values(
                "id",
                "name",
                "parent__name",
                "category__name",
                "category_min_id",
                "category_max_id",
                "category_avg_name_len",
                "span",
                "is_near_min",
                "name_twice",
                "score",
            )[:LIMIT_SELECT_BENCH],
        )

    def q6_plain_correlated_minmaxavg_equivalent_django_cte(self):
        return self._q6_explicit_cte(ExternalCTE, external_with_cte)

    def q6_plain_correlated_minmaxavg_equivalent_builtin_cte(self):
        return self._q6_explicit_cte(DjangoCTE, django_with_cte)


class CTESmokeBenchmarksTests(BenchmarkQueryMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cats = [NamedCategory.objects.create(name=f"cat{i}") for i in range(6)]
        tags = [Tag(name=f"tag_{i:04d}", category=cats[i % len(cats)]) for i in range(80)]
        Tag.objects.bulk_create(tags)
        tags = list(Tag.objects.order_by("pk")[:80])

        to_update = []
        for i in range(1, len(tags)):
            if i % 4 == 0:
                tags[i].parent = tags[i - 1]
                to_update.append(tags[i])
        Tag.objects.bulk_update(to_update, ["parent"])

        Tag.objects.create(name="", category=cats[0])
        Tag.objects.create(name="orphan", category=None)

    def _assert_rows(self, rows, required_keys):
        self.assertTrue(rows)
        self.assertLessEqual(len(rows), LIMIT_SELECT_BENCH)
        self.assertTrue(required_keys.issubset(rows[0].keys()))

    def test_benchmark_queries_execute_with_assertions(self):
        rows_q0 = list(self.q0_no_annotations())
        self._assert_rows(rows_q0, {"id", "name", "parent__name", "category__name"})

        rows_q1 = list(self.q1_nonduplicated_annotations())
        self._assert_rows(rows_q1, {"name_twice", "children_count", "category_tag_count", "score"})
        self.assertTrue(all(row["name_twice"] == f"{row['name']} {row['name']}" for row in rows_q1))
        self.assertTrue(all(row["category_tag_count"] >= 2 for row in rows_q1))

        rows_q2 = list(self.q2_duplicated_annotations())
        self._assert_rows(rows_q2, {"name_twice_twice", "name_upper_twice", "score"})
        self.assertTrue(
            all(row["name_upper_twice"] == f"{row['name_upper']}_{row['name_upper']}" for row in rows_q2)
        )

        rows_q3 = list(self.q3_parent_category_via_subquery())
        self._assert_rows(rows_q3, {"parent_name_sq", "category_name_sq", "has_children"})
        self.assertTrue(all(row["has_children"] for row in rows_q3))

        rows_q4 = list(self.q4_deep_duplication_chain(depth=6))
        self._assert_rows(rows_q4, {"a0", "a1", "a6"})
        self.assertTrue(all(row["a1"] == f"{row['a0']} {row['a0']}" for row in rows_q4))

        rows_q5 = list(self.q5_plain_correlated_preagg_equivalent())
        self._assert_rows(rows_q5, {"children_count", "category_tag_count", "score2"})
        self.assertTrue(all(row["category_tag_count"] >= 2 for row in rows_q5))

        rows_q6 = list(self.q6_plain_correlated_minmaxavg_equivalent())
        self._assert_rows(rows_q6, {"category_min_id", "category_max_id", "span", "score"})
        self.assertTrue(all(row["category_max_id"] >= row["category_min_id"] for row in rows_q6))

    def test_builtin_explicit_cte_matches_plain_query(self):
        plain_rows = list(self.q6_plain_correlated_minmaxavg_equivalent())
        builtin_rows = list(self.q6_plain_correlated_minmaxavg_equivalent_builtin_cte())

        self.assertEqual([row["id"] for row in plain_rows], [row["id"] for row in builtin_rows])
        for plain, builtin in zip(plain_rows, builtin_rows):
            self.assertEqual(plain["category_min_id"], builtin["category_min_id"])
            self.assertEqual(plain["category_max_id"], builtin["category_max_id"])
            self.assertEqual(plain["span"], builtin["span"])
            self.assertEqual(plain["score"], builtin["score"])
            self.assertAlmostEqual(
                float(plain["category_avg_name_len"]),
                float(builtin["category_avg_name_len"]),
                places=6,
            )


@skipUnless(HAS_DJANGO_CTE, "django-cte is not installed")
class ExternalCTECoexistenceTests(BenchmarkQueryMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        CTESmokeBenchmarksTests.setUpTestData()

    def test_external_explicit_cte_matches_plain_query(self):
        plain_rows = list(self.q6_plain_correlated_minmaxavg_equivalent())
        external_rows = list(self.q6_plain_correlated_minmaxavg_equivalent_django_cte())

        self.assertEqual([row["id"] for row in plain_rows], [row["id"] for row in external_rows])
        for plain, external in zip(plain_rows, external_rows):
            self.assertEqual(plain["category_min_id"], external["category_min_id"])
            self.assertEqual(plain["category_max_id"], external["category_max_id"])
            self.assertEqual(plain["span"], external["span"])
            self.assertEqual(plain["score"], external["score"])
            self.assertAlmostEqual(
                float(plain["category_avg_name_len"]),
                float(external["category_avg_name_len"]),
                places=6,
            )

    def test_external_and_builtin_ctes_can_be_used_together(self):
        builtin_cte = DjangoCTE(
            Tag.objects.values("category_id").annotate(category_total=Count("id")),
            name="builtin_totals",
        )
        external_cte = ExternalCTE(
            Tag.objects.values("category_id").annotate(category_max_id=Max("id")),
            name="external_totals",
        )

        qs = builtin_cte.join(Tag.objects.all(), category_id=builtin_cte.col.category_id).annotate(
            category_total=builtin_cte.col.category_total
        )
        qs = external_with_cte(
            external_cte,
            select=external_cte.join(qs, category_id=external_cte.col.category_id).annotate(
                category_max_id=external_cte.col.category_max_id
            ),
        )
        qs = django_with_cte(builtin_cte, select=qs).order_by("id").values(
            "id", "category_total", "category_max_id"
        )[:LIMIT_SELECT_BENCH]

        rows = list(qs)
        self.assertTrue(rows)
        self.assertTrue(all(row["category_total"] >= 1 for row in rows))
        self.assertTrue(all(row["category_max_id"] >= row["id"] for row in rows))


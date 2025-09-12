from unittest.mock import patch

from django.db import NotSupportedError, connection
from django.db.models import (
    Case,
    F,
    FilteredRelation,
    OuterRef,
    Q,
    Subquery,
    TextField,
    Value,
    When,
)
from django.db.models.functions import Cast
from django.db.models.lookups import Exact
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import Comment, Tenant, User


class CompositePKFilterTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.tenant_3 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1,
            id=1,
            email="user0001@example.com",
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_1,
            id=2,
            email="user0002@example.com",
        )
        cls.user_3 = User.objects.create(
            tenant=cls.tenant_2,
            id=3,
            email="user0003@example.com",
        )
        cls.user_4 = User.objects.create(
            tenant=cls.tenant_3,
            id=4,
            email="user0004@example.com",
        )
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_1)
        cls.comment_3 = Comment.objects.create(id=3, user=cls.user_2)
        cls.comment_4 = Comment.objects.create(id=4, user=cls.user_3)
        cls.comment_5 = Comment.objects.create(id=5, user=cls.user_1)

    def test_filter_and_count_user_by_pk(self):
        test_cases = (
            ({"pk": self.user_1.pk}, 1),
            ({"pk": self.user_2.pk}, 1),
            ({"pk": self.user_3.pk}, 1),
            ({"pk": (self.tenant_1.id, self.user_1.id)}, 1),
            ({"pk": (self.tenant_1.id, self.user_2.id)}, 1),
            ({"pk": (self.tenant_2.id, self.user_3.id)}, 1),
            ({"pk": (self.tenant_1.id, self.user_3.id)}, 0),
            ({"pk": (self.tenant_2.id, self.user_1.id)}, 0),
            ({"pk": (self.tenant_2.id, self.user_2.id)}, 0),
        )

        for lookup, count in test_cases:
            with self.subTest(lookup=lookup, count=count):
                self.assertEqual(User.objects.filter(**lookup).count(), count)

    def test_rhs_pk(self):
        msg = "CompositePrimaryKey cannot be used as a lookup value."
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.filter(text__gt=F("pk")).count()

    def test_rhs_combinable(self):
        msg = "CombinedExpression expression does not support composite primary keys."
        for expr in [F("pk") + (1, 1), (1, 1) + F("pk")]:
            with (
                self.subTest(expression=expr),
                self.assertRaisesMessage(ValueError, msg),
            ):
                Comment.objects.filter(text__gt=expr).count()

    def test_filter_comments_by_pk_gt(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        test_cases = (
            (c11, (c12, c13, c15, c24)),
            (c12, (c13, c15, c24)),
            (c13, (c15, c24)),
            (c15, (c24,)),
            (c24, ()),
        )

        for obj, objs in test_cases:
            with self.subTest(obj=obj, objs=objs):
                self.assertSequenceEqual(
                    Comment.objects.filter(pk__gt=obj.pk).order_by("pk"), objs
                )

    def test_filter_comments_by_pk_gte(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        test_cases = (
            (c11, (c11, c12, c13, c15, c24)),
            (c12, (c12, c13, c15, c24)),
            (c13, (c13, c15, c24)),
            (c15, (c15, c24)),
            (c24, (c24,)),
        )

        for obj, objs in test_cases:
            with self.subTest(obj=obj, objs=objs):
                self.assertSequenceEqual(
                    Comment.objects.filter(pk__gte=obj.pk).order_by("pk"), objs
                )

    def test_filter_comments_by_pk_lt(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        test_cases = (
            (c24, (c11, c12, c13, c15)),
            (c15, (c11, c12, c13)),
            (c13, (c11, c12)),
            (c12, (c11,)),
            (c11, ()),
        )

        for obj, objs in test_cases:
            with self.subTest(obj=obj, objs=objs):
                self.assertSequenceEqual(
                    Comment.objects.filter(pk__lt=obj.pk).order_by("pk"), objs
                )

    def test_filter_comments_by_pk_lte(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        test_cases = (
            (c24, (c11, c12, c13, c15, c24)),
            (c15, (c11, c12, c13, c15)),
            (c13, (c11, c12, c13)),
            (c12, (c11, c12)),
            (c11, (c11,)),
        )

        for obj, objs in test_cases:
            with self.subTest(obj=obj, objs=objs):
                self.assertSequenceEqual(
                    Comment.objects.filter(pk__lte=obj.pk).order_by("pk"), objs
                )

    def test_filter_comments_by_pk_in(self):
        test_cases = (
            (),
            (self.comment_1,),
            (self.comment_1, self.comment_4),
        )

        for objs in test_cases:
            with self.subTest(objs=objs):
                pks = [obj.pk for obj in objs]
                self.assertSequenceEqual(
                    Comment.objects.filter(pk__in=pks).order_by("pk"), objs
                )

    def test_filter_comments_by_pk_in_subquery(self):
        self.assertSequenceEqual(
            Comment.objects.filter(
                pk__in=Comment.objects.filter(pk=self.comment_1.pk),
            ),
            [self.comment_1],
        )
        self.assertSequenceEqual(
            Comment.objects.filter(
                pk__in=Comment.objects.filter(pk=self.comment_1.pk).values(
                    "tenant_id", "id"
                ),
            ),
            [self.comment_1],
        )
        self.comment_2.integer = self.comment_1.id
        self.comment_2.save()
        self.assertSequenceEqual(
            Comment.objects.filter(
                pk__in=Comment.objects.values("tenant_id", "integer"),
            ),
            [self.comment_1],
        )

    def test_filter_by_pk_in_subquery_invalid_selected_columns(self):
        msg = (
            "The QuerySet value for the 'in' lookup must have 2 selected "
            "fields (received 3)"
        )
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.filter(pk__in=Comment.objects.values("pk", "text"))

    def test_filter_by_pk_in_none(self):
        with self.assertNumQueries(0):
            self.assertSequenceEqual(
                Comment.objects.filter(pk__in=[(None, 1), (1, None)]),
                [],
            )

    def test_filter_comments_by_user_and_order_by_pk_asc(self):
        self.assertSequenceEqual(
            Comment.objects.filter(user=self.user_1).order_by("pk"),
            (self.comment_1, self.comment_2, self.comment_5),
        )

    def test_filter_comments_by_user_and_order_by_pk_desc(self):
        self.assertSequenceEqual(
            Comment.objects.filter(user=self.user_1).order_by("-pk"),
            (self.comment_5, self.comment_2, self.comment_1),
        )

    def test_filter_comments_by_user_and_exclude_by_pk(self):
        self.assertSequenceEqual(
            Comment.objects.filter(user=self.user_1)
            .exclude(pk=self.comment_1.pk)
            .order_by("pk"),
            (self.comment_2, self.comment_5),
        )

    def test_filter_comments_by_user_and_contains(self):
        self.assertIs(
            Comment.objects.filter(user=self.user_1).contains(self.comment_1), True
        )

    def test_filter_query_does_not_mutate(self):
        queryset = User.objects.filter(comments__in=Comment.objects.all())
        self.assertEqual(str(queryset.query), str(queryset.query))

    def test_filter_users_by_comments_in(self):
        c1, c2, c3, c4, c5 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        u1, u2, u3 = (
            self.user_1,
            self.user_2,
            self.user_3,
        )
        test_cases = (
            ((), ()),
            ((c1,), (u1,)),
            ((c1, c2), (u1, u1)),
            ((c1, c2, c3), (u1, u1, u2)),
            ((c1, c2, c3, c4), (u1, u1, u2, u3)),
            ((c1, c2, c3, c4, c5), (u1, u1, u1, u2, u3)),
        )

        for comments, users in test_cases:
            with self.subTest(comments=comments, users=users):
                self.assertSequenceEqual(
                    User.objects.filter(comments__in=comments).order_by("pk"), users
                )

    def test_filter_users_by_comments_lt(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        u1, u2 = (
            self.user_1,
            self.user_2,
        )
        test_cases = (
            (c11, ()),
            (c12, (u1,)),
            (c13, (u1, u1)),
            (c15, (u1, u1, u2)),
            (c24, (u1, u1, u1, u2)),
        )

        for comment, users in test_cases:
            with self.subTest(comment=comment, users=users):
                self.assertSequenceEqual(
                    User.objects.filter(comments__lt=comment).order_by("pk"), users
                )

    def test_filter_users_by_comments_lte(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        u1, u2, u3 = (
            self.user_1,
            self.user_2,
            self.user_3,
        )
        test_cases = (
            (c11, (u1,)),
            (c12, (u1, u1)),
            (c13, (u1, u1, u2)),
            (c15, (u1, u1, u1, u2)),
            (c24, (u1, u1, u1, u2, u3)),
        )

        for comment, users in test_cases:
            with self.subTest(comment=comment, users=users):
                self.assertSequenceEqual(
                    User.objects.filter(comments__lte=comment).order_by("pk"), users
                )

    def test_filter_users_by_comments_gt(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        u1, u2, u3 = (
            self.user_1,
            self.user_2,
            self.user_3,
        )
        test_cases = (
            (c11, (u1, u1, u2, u3)),
            (c12, (u1, u2, u3)),
            (c13, (u1, u3)),
            (c15, (u3,)),
            (c24, ()),
        )

        for comment, users in test_cases:
            with self.subTest(comment=comment, users=users):
                self.assertSequenceEqual(
                    User.objects.filter(comments__gt=comment).order_by("pk"), users
                )

    def test_filter_users_by_comments_gte(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        u1, u2, u3 = (
            self.user_1,
            self.user_2,
            self.user_3,
        )
        test_cases = (
            (c11, (u1, u1, u1, u2, u3)),
            (c12, (u1, u1, u2, u3)),
            (c13, (u1, u2, u3)),
            (c15, (u1, u3)),
            (c24, (u3,)),
        )

        for comment, users in test_cases:
            with self.subTest(comment=comment, users=users):
                self.assertSequenceEqual(
                    User.objects.filter(comments__gte=comment).order_by("pk"), users
                )

    def test_filter_users_by_comments_exact(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )
        u1, u2, u3 = (
            self.user_1,
            self.user_2,
            self.user_3,
        )
        test_cases = (
            (c11, (u1,)),
            (c12, (u1,)),
            (c13, (u2,)),
            (c15, (u1,)),
            (c24, (u3,)),
        )

        for comment, users in test_cases:
            with self.subTest(comment=comment, users=users):
                self.assertSequenceEqual(
                    User.objects.filter(comments=comment).order_by("pk"), users
                )

    def test_filter_users_by_comments_isnull(self):
        u1, u2, u3, u4 = (
            self.user_1,
            self.user_2,
            self.user_3,
            self.user_4,
        )

        with self.subTest("comments__isnull=True"):
            self.assertSequenceEqual(
                User.objects.filter(comments__isnull=True).order_by("pk"),
                (u4,),
            )
        with self.subTest("comments__isnull=False"):
            self.assertSequenceEqual(
                User.objects.filter(comments__isnull=False).order_by("pk"),
                (u1, u1, u1, u2, u3),
            )

    def test_filter_comments_by_pk_isnull(self):
        c11, c12, c13, c24, c15 = (
            self.comment_1,
            self.comment_2,
            self.comment_3,
            self.comment_4,
            self.comment_5,
        )

        with self.subTest("pk__isnull=True"):
            self.assertSequenceEqual(
                Comment.objects.filter(pk__isnull=True).order_by("pk"),
                (),
            )
        with self.subTest("pk__isnull=False"):
            self.assertSequenceEqual(
                Comment.objects.filter(pk__isnull=False).order_by("pk"),
                (c11, c12, c13, c15, c24),
            )

    def test_filter_users_by_comments_subquery(self):
        subquery = Comment.objects.filter(id=3).only("pk")
        queryset = User.objects.filter(comments__in=subquery)
        self.assertSequenceEqual(queryset, (self.user_2,))

    def test_cannot_cast_pk(self):
        msg = "Cast expression does not support composite primary keys."
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.filter(text__gt=Cast(F("pk"), TextField())).count()

    def test_explicit_subquery(self):
        subquery = Subquery(User.objects.values("pk"))
        self.assertEqual(User.objects.filter(pk__in=subquery).count(), 4)
        self.assertEqual(Comment.objects.filter(user__in=subquery).count(), 5)

    def test_filter_case_when(self):
        msg = "When expression does not support composite primary keys."
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.filter(text=Case(When(text="", then="pk")))
        msg = "Case expression does not support composite primary keys."
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.filter(text=Case(When(text="", then="text"), default="pk"))

    def test_outer_ref_pk(self):
        subquery = Subquery(Comment.objects.filter(pk=OuterRef("pk")).values("id")[:1])
        tests = [
            ("", 5),
            ("__gt", 0),
            ("__gte", 5),
            ("__lt", 0),
            ("__lte", 5),
        ]
        for lookup, expected_count in tests:
            with self.subTest(f"id{lookup}"):
                queryset = Comment.objects.filter(**{f"id{lookup}": subquery})
                self.assertEqual(queryset.count(), expected_count)

    def test_outer_ref_pk_filter_on_pk_exact(self):
        subquery = Subquery(User.objects.filter(pk=OuterRef("pk")).values("pk")[:1])
        qs = Comment.objects.filter(pk=subquery)
        self.assertEqual(qs.count(), 2)

    @skipUnlessDBFeature("supports_tuple_comparison_against_subquery")
    def test_outer_ref_pk_filter_on_pk_comparison(self):
        subquery = Subquery(User.objects.filter(pk=OuterRef("pk")).values("pk")[:1])
        tests = [
            ("gt", 0),
            ("gte", 2),
            ("lt", 0),
            ("lte", 2),
        ]
        for lookup, expected_count in tests:
            with self.subTest(f"pk__{lookup}"):
                qs = Comment.objects.filter(**{f"pk__{lookup}": subquery})
                self.assertEqual(qs.count(), expected_count)

    @skipIfDBFeature("supports_tuple_comparison_against_subquery")
    def test_outer_ref_pk_filter_on_pk_comparison_unsupported(self):
        subquery = Subquery(User.objects.filter(pk=OuterRef("pk")).values("pk")[:1])
        tests = ["gt", "gte", "lt", "lte"]
        for lookup in tests:
            with self.subTest(f"pk__{lookup}"):
                qs = Comment.objects.filter(**{f"pk__{lookup}": subquery})
                with self.assertRaisesMessage(
                    NotSupportedError,
                    f'"{lookup}" cannot be used to target composite fields '
                    "through subqueries on this backend",
                ):
                    qs.count()

    def test_unsupported_rhs(self):
        pk = Exact(F("tenant_id"), 1)
        msg = (
            "'exact' subquery lookup of 'pk' only supports OuterRef "
            "and QuerySet objects (received 'Exact')"
        )
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.filter(pk=pk)

    @skipUnlessDBFeature("allow_sliced_subqueries_with_in")
    def test_filter_comments_by_pk_exact_subquery(self):
        self.assertSequenceEqual(
            Comment.objects.filter(
                pk=Comment.objects.filter(pk=self.comment_1.pk)[:1],
            ),
            [self.comment_1],
        )
        self.assertSequenceEqual(
            Comment.objects.filter(
                pk__in=Comment.objects.filter(pk=self.comment_1.pk).values(
                    "tenant_id", "id"
                )[:1],
            ),
            [self.comment_1],
        )
        self.comment_2.integer = self.comment_1.id
        self.comment_2.save()
        self.assertSequenceEqual(
            Comment.objects.filter(
                pk__in=Comment.objects.values("tenant_id", "integer"),
            )[:1],
            [self.comment_1],
        )

    def test_outer_ref_not_composite_pk(self):
        subquery = Comment.objects.filter(pk=OuterRef("id")).values("id")[:1]
        queryset = Comment.objects.filter(id=Subquery(subquery))

        msg = "Composite field lookups only work with composite expressions."
        with self.assertRaisesMessage(ValueError, msg):
            self.assertEqual(queryset.count(), 5)

    def test_outer_ref_in_filtered_relation(self):
        msg = (
            "This queryset contains a reference to an outer query and may only be used "
            "in a subquery."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.assertSequenceEqual(
                Tenant.objects.annotate(
                    filtered_tokens=FilteredRelation(
                        "tokens",
                        condition=Q(tokens__pk__gte=OuterRef("tokens")),
                    )
                ).filter(filtered_tokens=(1, 1)),
                [self.tenant_1],
            )

    def test_filter_by_tuple_containing_expression(self):
        pk_lookup = (self.comment_1.tenant.id, (Value(self.comment_1.id) + 1) - 1)
        for lookup in ({"pk": pk_lookup}, {"pk__in": [pk_lookup]}):
            with self.subTest(lookup=lookup):
                qs = Comment.objects.filter(**lookup)
                self.assertEqual(qs.get(), self.comment_1)


@skipUnlessDBFeature("supports_tuple_lookups")
class CompositePKFilterTupleLookupFallbackTests(CompositePKFilterTests):
    def setUp(self):
        feature_patch_1 = patch.object(
            connection.features, "supports_tuple_lookups", False
        )
        feature_patch_2 = patch.object(
            connection.features, "supports_tuple_comparison_against_subquery", False
        )
        self.enterContext(feature_patch_1)
        self.enterContext(feature_patch_2)

from django.db.models import F, Q
from django.test import TestCase

from .models import Comment, Tenant, Token


class CompositePKSubqueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.token = Token.objects.create(
            tenant=cls.tenant,
            id=1,
            secret="secret",
        )
        cls.other_token = Token.objects.create(tenant=cls.tenant, id=2)
        cls.other_tenant = Tenant.objects.create()
        cls.other_tenant_token = Token.objects.create(tenant=cls.other_tenant, id=0)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1)

    def test_select_composite_primary_key_and_scalar_field(self):
        token_info = Token.objects.filter(pk=self.token.pk).values("pk", "secret")[:1]
        token_data = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .values_list("token_info__pk", "token_info__secret")
        )

        self.assertSequenceEqual(token_data, [(self.token.pk, self.token.secret)])

    def test_select_only_composite_primary_key(self):
        token_info = Token.objects.filter(pk=self.token.pk).values("pk")[:1]
        token_pks = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .values_list("token_info__pk", flat=True)
        )

        self.assertSequenceEqual(token_pks, [self.token.pk])

    def test_filter_composite_primary_key(self):
        token_info = Token.objects.filter(pk=self.token.pk).values("pk")[:1]
        tokens = Token.objects.filter(pk=self.token.pk).alias(token_info=token_info)

        self.assertSequenceEqual(
            tokens.filter(token_info__pk=self.token.pk).values_list("pk", flat=True),
            [self.token.pk],
        )
        self.assertFalse(tokens.filter(token_info__pk=self.other_token.pk).exists())

    def test_filter_composite_primary_key_and_scalar_field(self):
        token_info = Token.objects.filter(pk=self.token.pk).values("pk", "secret")[:1]
        token_pks = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .filter(token_info=(*self.token.pk, self.token.secret))
            .values_list("pk", flat=True)
        )

        self.assertSequenceEqual(token_pks, [self.token.pk])

    def test_filter_composite_primary_key_expression(self):
        token_info = Token.objects.filter(pk=self.token.pk).values("pk")[:1]
        token_pks = (
            Token.objects.alias(token_info=token_info)
            .filter(token_info__pk=F("pk"))
            .values_list("pk", flat=True)
        )

        self.assertSequenceEqual(token_pks, [self.token.pk])

    def test_order_by_composite_primary_key(self):
        token_info = Token.objects.values("pk")
        token_pks = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .order_by("-token_info__pk")
            .values_list("token_info__pk", flat=True)
        )

        self.assertSequenceEqual(
            token_pks,
            [self.other_tenant_token.pk, self.other_token.pk, self.token.pk],
        )

    def test_order_by_then_filter_composite_primary_key(self):
        token_info = Token.objects.values("pk")
        token_pks = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .order_by("-token_info__pk")
            .filter(token_info__pk__gte=self.token.pk)
            .values_list("token_info__pk", flat=True)
        )

        self.assertSequenceEqual(
            token_pks,
            [self.other_tenant_token.pk, self.other_token.pk, self.token.pk],
        )

    def test_or_filter_preserves_outer_row(self):
        missing_token = Token.objects.filter(pk=(-1, -1)).values("pk")
        token_pks = (
            Token.objects.alias(token_info=missing_token)
            .filter(Q(token_info__pk=self.token.pk) | Q(pk=self.other_token.pk))
            .values_list("pk", flat=True)
        )

        self.assertSequenceEqual(token_pks, [self.other_token.pk])

    def test_exclude_composite_primary_key_from_empty_subquery(self):
        missing_token = Token.objects.filter(pk=(-1, -1)).values("pk")
        token_pks = (
            Token.objects.alias(token_info=missing_token)
            .exclude(token_info__pk=self.token.pk)
            .order_by("tenant_id", "id")
            .values_list("pk", flat=True)
        )

        self.assertSequenceEqual(
            token_pks,
            [self.token.pk, self.other_token.pk, self.other_tenant_token.pk],
        )

    def test_select_composite_primary_key_and_component(self):
        token_info = Token.objects.filter(pk=self.token.pk).values("pk", "tenant_id")[
            :1
        ]
        token_data = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .values_list("token_info__pk", "token_info__tenant_id")
        )

        self.assertSequenceEqual(
            token_data,
            [(self.token.pk, self.token.tenant_id)],
        )

    def test_select_composite_primary_key_component_db_column(self):
        comment_info = Comment.objects.filter(pk=self.comment.pk).values("pk")[:1]
        comment_data = (
            Comment.objects.filter(pk=self.comment.pk)
            .alias(comment_info=comment_info)
            .values_list("comment_info__pk", flat=True)
        )

        self.assertSequenceEqual(comment_data, [self.comment.pk])

    def test_combined_query_composite_primary_key(self):
        token_info = (
            Token.objects.filter(pk=self.token.pk)
            .values("pk", "secret")
            .union(Token.objects.filter(pk=(-1, -1)).values("pk", "secret"))[:1]
        )
        token_pks = (
            Token.objects.filter(pk=self.token.pk)
            .alias(token_info=token_info)
            .values_list("token_info__pk", flat=True)
        )

        self.assertSequenceEqual(token_pks, [self.token.pk])

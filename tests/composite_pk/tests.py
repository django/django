from django.db.models.query_utils import PathInfo
from django.db.models.sql import Query
from django.test import TestCase

from .models import Tenant, TenantUser, TenantUserComment


class CompositePKTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = TenantUser.objects.create(tenant=cls.tenant, id=1)
        cls.comment = TenantUserComment.objects.create(
            tenant=cls.tenant, id=1, user=cls.user
        )

    def test_fields(self):
        # tenant
        self.assertIsInstance(self.tenant.pk, int)
        self.assertGreater(self.tenant.id, 0)
        self.assertEqual(self.tenant.pk, self.tenant.id)

        # user
        self.assertIsInstance(self.user.id, int)
        self.assertGreater(self.user.id, 0)
        self.assertEqual(self.user.tenant_id, self.tenant.id)
        self.assertEqual(self.user.pk, (self.user.tenant_id, self.user.id))

        # comment
        self.assertIsInstance(self.comment.id, int)
        self.assertGreater(self.comment.id, 0)
        self.assertEqual(self.comment.user_id, self.user.id)
        self.assertEqual(self.comment.tenant_id, self.tenant.id)
        self.assertEqual(self.comment.pk, (self.comment.tenant_id, self.comment.id))

    def test_delete_tenant_by_id(self):
        Tenant.objects.filter(id=self.tenant.id).delete()

        self.assertFalse(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.user.id).exists())
        self.assertFalse(TenantUserComment.objects.filter(id=self.comment.id).exists())

    def test_delete_tenant_by_pk(self):
        Tenant.objects.filter(pk=self.tenant.id).delete()

        self.assertFalse(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.user.id).exists())
        self.assertFalse(TenantUserComment.objects.filter(id=self.comment.id).exists())

    def test_delete_user_by_id(self):
        TenantUser.objects.filter(id=self.user.id).delete()

        self.assertTrue(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.user.id).exists())
        self.assertFalse(TenantUserComment.objects.filter(id=self.comment.id).exists())

    def test_delete_user_by_pk(self):
        TenantUser.objects.filter(pk=self.user.pk).delete()

        self.assertTrue(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.user.id).exists())
        self.assertFalse(TenantUserComment.objects.filter(id=self.comment.id).exists())

    def test_get_by_pk(self):
        # tenant
        self.assertEqual(Tenant.objects.get(pk=self.tenant.id), self.tenant)
        self.assertEqual(Tenant.objects.get(id=self.tenant.id), self.tenant)

        # user
        self.assertEqual(
            TenantUser.objects.get(pk=(self.tenant.id, self.user.id)), self.user
        )
        self.assertEqual(TenantUser.objects.get(id=self.user.id), self.user)
        self.assertEqual(TenantUser.objects.get(tenant_id=self.tenant.id), self.user)

        # comment
        self.assertEqual(
            TenantUserComment.objects.get(pk=(self.tenant.id, self.comment.id)),
            self.comment,
        )
        self.assertEqual(
            TenantUserComment.objects.get(id=self.comment.id), self.comment
        )
        self.assertEqual(
            TenantUserComment.objects.get(tenant_id=self.tenant.id), self.comment
        )


class NamesToPathTests(TestCase):
    def test_id(self):
        query = Query(TenantUser)
        path, final_field, targets, rest = query.names_to_path(["id"], TenantUser._meta)

        self.assertEqual(path, [])
        self.assertEqual(final_field, TenantUser._meta.get_field("id"))
        self.assertEqual(targets, (TenantUser._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_pk(self):
        query = Query(TenantUser)
        path, final_field, targets, rest = query.names_to_path(["pk"], TenantUser._meta)

        self.assertEqual(path, [])
        self.assertEqual(final_field, TenantUser._meta.get_field("_pk"))
        self.assertEqual(targets, (TenantUser._meta.get_field("_pk"),))
        self.assertEqual(rest, [])

    def test_tenant_id(self):
        query = Query(TenantUser)
        path, final_field, targets, rest = query.names_to_path(
            ["tenant", "id"], TenantUser._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=TenantUser._meta,
                    to_opts=Tenant._meta,
                    target_fields=(Tenant._meta.get_field("id"),),
                    join_field=TenantUser._meta.get_field("tenant"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, Tenant._meta.get_field("id"))
        self.assertEqual(targets, (Tenant._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_user_id(self):
        query = Query(TenantUserComment)
        path, final_field, targets, rest = query.names_to_path(
            ["user", "id"], TenantUserComment._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=TenantUserComment._meta,
                    to_opts=TenantUser._meta,
                    target_fields=(
                        TenantUser._meta.get_field("tenant"),
                        TenantUser._meta.get_field("id"),
                    ),
                    join_field=TenantUserComment._meta.get_field("user"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, TenantUser._meta.get_field("id"))
        self.assertEqual(targets, (TenantUser._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_user_tenant_id(self):
        query = Query(TenantUserComment)
        path, final_field, targets, rest = query.names_to_path(
            ["user", "tenant", "id"], TenantUserComment._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=TenantUserComment._meta,
                    to_opts=TenantUser._meta,
                    target_fields=(
                        TenantUser._meta.get_field("tenant"),
                        TenantUser._meta.get_field("id"),
                    ),
                    join_field=TenantUserComment._meta.get_field("user"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
                PathInfo(
                    from_opts=TenantUser._meta,
                    to_opts=Tenant._meta,
                    target_fields=(Tenant._meta.get_field("id"),),
                    join_field=TenantUser._meta.get_field("tenant"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, Tenant._meta.get_field("id"))
        self.assertEqual(targets, (Tenant._meta.get_field("id"),))
        self.assertEqual(rest, [])

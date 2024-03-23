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

    def test_cascade_delete_on_tenant_delete(self):
        Tenant.objects.filter(id=self.tenant.id).delete()

        self.assertFalse(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.user.id).exists())
        self.assertFalse(TenantUserComment.objects.filter(id=self.comment.id).exists())

    def test_cascade_delete_on_user_delete(self):
        TenantUser.objects.filter(id=self.user.id).delete()

        self.assertTrue(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.user.id).exists())
        self.assertFalse(TenantUserComment.objects.filter(id=self.comment.id).exists())

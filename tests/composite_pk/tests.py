from django.test import TestCase

from .models import Tenant, TenantUser, TenantUserComment


class CompositeFKTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.tenant_user = TenantUser.objects.create(tenant=cls.tenant, id=1)

    def test_cascading_deletes_on_tenant_delete(self):
        Tenant.objects.filter(id=self.tenant.id).delete()
        self.assertFalse(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(TenantUser.objects.filter(id=self.tenant_user.id).exists())

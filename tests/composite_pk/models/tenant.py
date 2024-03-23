from django.db import models


class Tenant(models.Model):
    pass


class TenantUser(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    id = models.IntegerField()

    class Meta:
        primary_key = ("tenant_id", "id")


class TenantUserComment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    id = models.IntegerField()
    user_id = models.IntegerField()
    user = models.ForeignObject(
        TenantUser,
        on_delete=models.CASCADE,
        from_fields=("tenant_id", "user_id"),
        to_fields=("tenant_id", "id"),
    )

    class Meta:
        primary_key = ("tenant_id", "id")

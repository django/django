from django.db import models


class Tenant(models.Model):
    pass


class User(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("tenant_id", "id")


class Comment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        from_fields=("tenant_id", "user_id"),
        to_fields=("tenant_id", "id"),
        related_name="comments",
    )

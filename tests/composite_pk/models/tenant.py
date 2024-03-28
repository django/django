from django.db import connection, models


class Tenant(models.Model):
    pass


class User(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # SQLite doesn't support non-primary auto fields.
    if connection.vendor == "sqlite":
        id = models.SmallIntegerField()
    else:
        id = models.SmallAutoField()

    class Meta:
        primary_key = ("tenant_id", "id")


class Comment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # SQLite doesn't support non-primary auto fields.
    if connection.vendor == "sqlite":
        id = models.SmallIntegerField()
    else:
        id = models.SmallAutoField()
    user_id = models.SmallIntegerField()
    user = models.ForeignObject(
        User,
        on_delete=models.CASCADE,
        from_fields=("tenant_id", "user_id"),
        to_fields=("tenant_id", "id"),
        related_name="+",
    )

    class Meta:
        primary_key = ("tenant_id", "id")

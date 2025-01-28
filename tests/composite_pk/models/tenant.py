import uuid

from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=10, default="", blank=True)


class Token(models.Model):
    pk = models.CompositePrimaryKey("tenant_id", "id")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tokens")
    id = models.SmallIntegerField()
    secret = models.CharField(max_length=10, default="", blank=True)


class BaseModel(models.Model):
    pk = models.CompositePrimaryKey("tenant_id", "id")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    id = models.SmallIntegerField(unique=True)

    class Meta:
        abstract = True


class User(BaseModel):
    email = models.EmailField(unique=True)


class Comment(models.Model):
    pk = models.CompositePrimaryKey("tenant", "id")
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    id = models.SmallIntegerField(unique=True, db_column="comment_id")
    user_id = models.SmallIntegerField()
    user = models.ForeignObject(
        User,
        on_delete=models.CASCADE,
        from_fields=("tenant_id", "user_id"),
        to_fields=("tenant_id", "id"),
        related_name="comments",
    )
    text = models.TextField(default="", blank=True)
    integer = models.IntegerField(default=0)


class Post(models.Model):
    pk = models.CompositePrimaryKey("tenant_id", "id")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=1)
    id = models.UUIDField(default=uuid.uuid4)


class TimeStamped(models.Model):
    pk = models.CompositePrimaryKey("id", "created")
    id = models.SmallIntegerField(unique=True)
    created = models.DateTimeField(auto_now_add=True)
    text = models.TextField(default="", blank=True)

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
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


class Post(models.Model):
    pk = models.CompositePrimaryKey("tenant_id", "id")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    id = models.UUIDField()
    tags = GenericRelation("Tag", related_query_name="post")


class Tag(models.Model):
    name = models.CharField(max_length=10)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="composite_pk_tags"
    )
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey("content_type", "object_id")

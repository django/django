from django.db import models


class OtherAuthor(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(null=True)
    age = models.IntegerField(default=0)
    silly_field = models.BooleanField(default=False)

    class Meta:
        app_label = "migrated_unapplied_app"

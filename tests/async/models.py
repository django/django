from django.db import models
from django.utils import timezone


class RelatedModel(models.Model):
    simple = models.ForeignKey("SimpleModel", models.CASCADE, null=True)


class SimpleModel(models.Model):
    field = models.IntegerField()
    created = models.DateTimeField(default=timezone.now)


class ManyToManyModel(models.Model):
    simples = models.ManyToManyField("SimpleModel")


class IncrementASaveModel(models.Model):
    field = models.IntegerField()

    async def asave(self, *args, **kwargs):
        self.field += 1
        await super().asave(*args, **kwargs)

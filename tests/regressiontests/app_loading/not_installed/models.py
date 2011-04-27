from django.db import models


class NotInstalledModel(models.Model):
    pass


class RelatedModel(models.Model):
    not_installed = models.ForeignKey(NotInstalledModel)


class M2MRelatedModel(models.Model):
    not_installed = models.ManyToManyField(NotInstalledModel)

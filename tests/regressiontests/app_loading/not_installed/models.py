from django.db import models


class NotInstalledModel(models.Model):
    pass


class RelatedModel(models.Model):
    not_installed = models.ForeignKey(NotInstalledModel)

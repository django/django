from django.db import models


class NotInstalledModel(models.Model):

    class Meta:
        app_label = 'not_installed'


class RelatedModel(models.Model):

    class Meta:
        app_label = 'not_installed'

    not_installed = models.ForeignKey(NotInstalledModel, models.CASCADE)


class M2MRelatedModel(models.Model):

    class Meta:
        app_label = 'not_installed'

    not_installed = models.ManyToManyField(NotInstalledModel)

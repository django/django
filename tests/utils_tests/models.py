from django.contrib.contenttypes.fields import GenericRelation
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)


class CategoryInfo(models.Model):
    category = models.OneToOneField(Category, models.CASCADE)


class GenericModel(models.Model):
    name = models.CharField(max_length=255)


class CustomSaveModel(models.Model):
    name = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        return super(CustomSaveModel, self).save(*args, **kwargs)


class ExplicitAlterDataModel(models.Model):
    name = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        return super(ExplicitAlterDataModel, self).save(*args, **kwargs)

    save.alters_data = False


class Host(models.Model):
    name = models.CharField(max_length=255)


class Document(models.Model):
    file_path = models.FileField()


class AuditLog(models.Model):
    host = models.ForeignKey(
        to=Host, on_delete=models.PROTECT, related_name='logs'
    )
    log_file = models.ForeignKey(
        to=Document, on_delete=models.PROTECT, related_name='audits', null=True
    )


class Process(models.Model):
    name = models.CharField(max_length=255)
    logs = models.ManyToManyField(AuditLog, related_name='processes')
    tags = GenericRelation(GenericModel, related_query_name='processes')

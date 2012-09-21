from django.db import models

class AltManager(models.Manager):
    pass

class Item(models.Model):
    name = models.CharField(max_length=20)
    created = models.DateTimeField()
    int_value = models.IntegerField(blank=True, null=True)
    parent = models.ForeignKey('self', related_name='children', null=True)
    objects = models.Manager()
    alt_manager = AltManager()

class OtherItem(models.Model):
    name = models.CharField(max_length=20)
    created = models.DateTimeField()
    int_value = models.IntegerField(blank=True, null=True)


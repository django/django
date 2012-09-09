from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=20)
    created = models.DateTimeField()
    int_value = models.IntegerField(blank=True, null=True)
    parent = models.ForeignKey('self', related_name='children', null=True)



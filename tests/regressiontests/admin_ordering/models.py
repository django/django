# coding: utf-8
from django.db import models

class Band(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField()
    rank = models.IntegerField()

    class Meta:
        ordering = ('name',)

__test__ = {'API_TESTS': """

Let's make sure that ModelAdmin.queryset uses the ordering we define in
ModelAdmin rather that ordering defined in the model's inner Meta
class.

>>> from django.contrib.admin.options import ModelAdmin

>>> b1 = Band(name='Aerosmith', bio='', rank=3)
>>> b1.save()
>>> b2 = Band(name='Radiohead', bio='', rank=1)
>>> b2.save()
>>> b3 = Band(name='Van Halen', bio='', rank=2)
>>> b3.save()

The default ordering should be by name, as specified in the inner Meta class.

>>> ma = ModelAdmin(Band, None)
>>> [b.name for b in ma.queryset(None)]
[u'Aerosmith', u'Radiohead', u'Van Halen']


Let's use a custom ModelAdmin that changes the ordering, and make sure it
actually changes.

>>> class BandAdmin(ModelAdmin):
...     ordering = ('rank',) # default ordering is ('name',)
...

>>> ma = BandAdmin(Band, None)
>>> [b.name for b in ma.queryset(None)]
[u'Radiohead', u'Van Halen', u'Aerosmith']

"""
}

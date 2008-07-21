"""
Regression tests for an object that cannot access a single related object due
to a restrictive default manager.
"""

from django.db import models


class SourceManager(models.Manager):
    def get_query_set(self):
        return super(SourceManager, self).get_query_set().filter(is_public=True)

class Source(models.Model):
    is_public = models.BooleanField()
    objects = SourceManager()

class Item(models.Model):
    source = models.ForeignKey(Source)


__test__ = {'API_TESTS':"""

>>> public_source = Source.objects.create(is_public=True)
>>> public_item = Item.objects.create(source=public_source)

>>> private_source = Source.objects.create(is_public=False)
>>> private_item = Item.objects.create(source=private_source)

Only one source is available via all() due to the custom default manager.

>>> Source.objects.all()
[<Source: Source object>]

>>> public_item.source
<Source: Source object>

Make sure that an item can still access its related source even if the default
manager doesn't normally allow it.

>>> private_item.source
<Source: Source object>

"""}

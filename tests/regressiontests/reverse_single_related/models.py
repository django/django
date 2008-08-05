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

# Only one source is available via all() due to the custom default manager.

>>> Source.objects.all()
[<Source: Source object>]

>>> public_item.source
<Source: Source object>

# Make sure that an item can still access its related source even if the default
# manager doesn't normally allow it.

>>> private_item.source
<Source: Source object>

# If the manager is marked "use_for_related_fields", it'll get used instead
# of the "bare" queryset. Usually you'd define this as a property on the class,
# but this approximates that in a way that's easier in tests.

>>> Source.objects.use_for_related_fields = True
>>> private_item = Item.objects.get(pk=private_item.pk)
>>> private_item.source
Traceback (most recent call last):
    ...
DoesNotExist: Source matching query does not exist.

"""}

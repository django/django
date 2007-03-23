"""
39. Empty model tests

These test that things behave sensibly for the rare corner-case of a model with
no fields.
"""

from django.db import models

class Empty(models.Model):
    pass

__test__ = {'API_TESTS':"""
>>> m = Empty()
>>> m.id
>>> m.save()
>>> m2 = Empty()
>>> m2.save()
>>> len(Empty.objects.all())
2
>>> m.id is not None
True
>>> existing = Empty(m.id)
>>> existing.save()

"""}

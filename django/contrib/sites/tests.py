"""
>>> # Make sure that get_current() does not return a deleted Site object.
>>> from django.contrib.sites.models import Site
>>> s = Site.objects.get_current()
>>> isinstance(s, Site)
True

>>> s.delete()
>>> Site.objects.get_current()
Traceback (most recent call last):
...
DoesNotExist: Site matching query does not exist.
"""

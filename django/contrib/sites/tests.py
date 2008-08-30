"""
>>> from django.contrib.sites.models import Site
>>> from django.conf import settings
>>> Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()

>>> # Make sure that get_current() does not return a deleted Site object.
>>> s = Site.objects.get_current()
>>> isinstance(s, Site)
True

>>> s.delete()
>>> Site.objects.get_current()
Traceback (most recent call last):
...
DoesNotExist: Site matching query does not exist.
"""

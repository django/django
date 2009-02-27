"""
>>> from django.contrib.sites.models import Site
>>> from django.conf import settings
>>> Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()

# Make sure that get_current() does not return a deleted Site object.
>>> s = Site.objects.get_current()
>>> isinstance(s, Site)
True

>>> s.delete()
>>> Site.objects.get_current()
Traceback (most recent call last):
...
DoesNotExist: Site matching query does not exist.

# After updating a Site object (e.g. via the admin), we shouldn't return a
# bogus value from the SITE_CACHE.
>>> _ = Site.objects.create(id=settings.SITE_ID, domain="example.com", name="example.com")
>>> site = Site.objects.get_current()
>>> site.name
u"example.com"
>>> s2 = Site.objects.get(id=settings.SITE_ID)
>>> s2.name = "Example site"
>>> s2.save()
>>> site = Site.objects.get_current()
>>> site.name
u"Example site"
"""

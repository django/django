import re
from django.conf import settings
from django.conf.urls.defaults import patterns, url, include
from django.core.exceptions import ImproperlyConfigured

urlpatterns = []

# only serve non-fqdn URLs
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),
    )

def staticfiles_urlpatterns(prefix=None):
    """
    Helper function to return a URL pattern for serving static files.
    """
    if not settings.DEBUG:
        return []
    if prefix is None:
        prefix = settings.STATIC_URL
    if not prefix or '://' in prefix:
        raise ImproperlyConfigured(
            "The prefix for the 'staticfiles_urlpatterns' helper is invalid.")
    if prefix.startswith("/"):
        prefix = prefix[1:]
    return patterns('',
        url(r'^%s' % re.escape(prefix), include(urlpatterns)),)

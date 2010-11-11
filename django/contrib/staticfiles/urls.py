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
        prefix = settings.STATICFILES_URL
    if not prefix:
        raise ImproperlyConfigured(
            "The prefix for the 'staticfiles_urlpatterns' helper is empty. "
            "Make sure the STATICFILES_URL setting is set correctly.")
    if '://' in prefix:
        raise ImproperlyConfigured(
            "The STATICFILES_URL setting is a full URL, not a path and "
            "can't be used with the 'staticfiles_urlpatterns' helper.")
    if prefix.startswith("/"):
        prefix = prefix[1:]
    return patterns('',
        url(r'^%s' % re.escape(prefix), include(urlpatterns)),)

import re
from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.core.exceptions import ImproperlyConfigured

def static(prefix, view='django.views.static.serve', **kwargs):
    """
    Helper function to return a URL pattern for serving files in debug mode.

    from django.conf import settings
    from django.conf.urls.static import static

    urlpatterns = patterns('',
        # ... the rest of your URLconf goes here ...
    ) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    """
    # No-op if not in debug mode or an non-local prefix
    if not settings.DEBUG or (prefix and '://' in prefix):
        return []
    elif not prefix:
        raise ImproperlyConfigured("Empty static prefix not permitted")
    return patterns('',
        url(r'^%s(?P<path>.*)$' % re.escape(prefix.lstrip('/')), view, kwargs=kwargs),
    )

import re
from urllib.parse import urlsplit

from thibaud.conf import settings
from thibaud.core.exceptions import ImproperlyConfigured
from thibaud.urls import re_path
from thibaud.views.static import serve


def static(prefix, view=serve, **kwargs):
    """
    Return a URL pattern for serving files in debug mode.

    from thibaud.conf import settings
    from thibaud.conf.urls.static import static

    urlpatterns = [
        # ... the rest of your URLconf goes here ...
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    """
    if not prefix:
        raise ImproperlyConfigured("Empty static prefix not permitted")
    elif not settings.DEBUG or urlsplit(prefix).netloc:
        # No-op if not in debug mode or a non-local prefix.
        return []
    return [
        re_path(
            r"^%s(?P<path>.*)$" % re.escape(prefix.lstrip("/")), view, kwargs=kwargs
        ),
    ]

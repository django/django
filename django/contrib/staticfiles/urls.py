from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve

def staticfiles_urlpatterns(prefix=None):
    """
    Helper function to return a URL pattern for serving static files.
    """
    if prefix is None:
        prefix = settings.STATIC_URL
    return static(prefix, view=serve)

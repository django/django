"""
Views and functions for serving static files. These are only to be used during
development, and SHOULD NOT be used in a production setting.

"""
import os
import posixpath

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import Http404
from django.views.static import ServeStatic


def serve(request, path, insecure=False, **kwargs):
    assert False


class Serve(ServeStatic):
    insecure = False

    def get(self, request, path):
        """
        Serve static files below a given point in the directory structure or
        from locations inferred from the staticfiles finders.

        To use, put a URL pattern such as::

            from django.contrib.staticfiles import views

            url(r'^(?P<path>.*)$', views.serve)

        in your URLconf.

        It uses the django.views.static.serve() view to serve the found files.
        """
        if not settings.DEBUG and not self.insecure:
            raise Http404
        normalized_path = posixpath.normpath(path).lstrip('/')
        absolute_path = finders.find(normalized_path)
        if not absolute_path:
            if path.endswith('/') or path == '':
                raise Http404("Directory indexes are not allowed here.")
            raise Http404("'%s' could not be found" % path)
        self.document_root, path = os.path.split(absolute_path)
        return super().get(request, path)

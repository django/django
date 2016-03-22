from __future__ import unicode_literals

from django.conf import settings
from django.contrib.staticfiles import utils
from django.contrib.staticfiles.views import serve
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.six.moves.urllib.request import url2pathname

from .handler import AsgiHandler, ViewConsumer


class StaticFilesHandler(AsgiHandler):
    """
    Wrapper handler that serves the static files directory.
    """

    def __init__(self, *args, **kwargs):
        super(StaticFilesHandler, self).__init__()
        self.base_url = urlparse(self.get_base_url())

    def get_base_url(self):
        utils.check_settings()
        return settings.STATIC_URL

    def _should_handle(self, path):
        """
        Checks if the path should be handled. Ignores the path if:

        * the host is provided as part of the base_url
        * the request's path isn't under the media path (or equal)
        """
        return path.startswith(self.base_url[2]) and not self.base_url[1]

    def file_path(self, url):
        """
        Returns the relative path to the media file on disk for the given URL.
        """
        relative_url = url[len(self.base_url[2]):]
        return url2pathname(relative_url)

    def serve(self, request):
        """
        Actually serves the request path.
        """
        return serve(request, self.file_path(request.path), insecure=True)

    def get_response(self, request):
        from django.http import Http404

        if self._should_handle(request.path):
            try:
                return self.serve(request)
            except Http404 as e:
                if settings.DEBUG:
                    from django.views import debug
                    return debug.technical_404_response(request, e)
        return super(StaticFilesHandler, self).get_response(request)


class StaticFilesConsumer(ViewConsumer):
    """
    Overrides standard view consumer with our new handler
    """

    handler_class = StaticFilesHandler

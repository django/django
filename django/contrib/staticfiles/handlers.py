import urllib
from urlparse import urlparse

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler

from django.contrib.staticfiles import utils
from django.contrib.staticfiles.views import serve

class StaticFilesHandler(WSGIHandler):
    """
    WSGI middleware that intercepts calls to the static files directory, as
    defined by the STATIC_URL setting, and serves those files.
    """
    def __init__(self, application, base_dir=None):
        self.application = application
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = self.get_base_dir()
        self.base_url = urlparse(self.get_base_url())
        super(StaticFilesHandler, self).__init__()

    def get_base_dir(self):
        return settings.STATIC_ROOT

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
        return urllib.url2pathname(relative_url)

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
            except Http404, e:
                if settings.DEBUG:
                    from django.views import debug
                    return debug.technical_404_response(request, e)
        return super(StaticFilesHandler, self).get_response(request)

    def __call__(self, environ, start_response):
        if not self._should_handle(environ['PATH_INFO']):
            return self.application(environ, start_response)
        return super(StaticFilesHandler, self).__call__(environ, start_response)

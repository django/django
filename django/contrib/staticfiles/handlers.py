import urllib
from urlparse import urlparse

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler

from django.contrib.staticfiles import utils
from django.contrib.staticfiles.views import serve

class StaticFilesHandler(WSGIHandler):
    """
    WSGI middleware that intercepts calls to the static files directory, as
    defined by the STATICFILES_URL setting, and serves those files.
    """
    def __init__(self, application, media_dir=None):
        self.application = application
        if media_dir:
            self.media_dir = media_dir
        else:
            self.media_dir = self.get_media_dir()
        self.media_url = urlparse(self.get_media_url())
        if settings.DEBUG:
            utils.check_settings()
        super(StaticFilesHandler, self).__init__()

    def get_media_dir(self):
        return settings.STATICFILES_ROOT

    def get_media_url(self):
        return settings.STATICFILES_URL

    def _should_handle(self, path):
        """
        Checks if the path should be handled. Ignores the path if:

        * the host is provided as part of the media_url
        * the request's path isn't under the media path (or equal)
        * settings.DEBUG isn't True
        """
        return (self.media_url[2] != path and
            path.startswith(self.media_url[2]) and not self.media_url[1])

    def file_path(self, url):
        """
        Returns the relative path to the media file on disk for the given URL.

        The passed URL is assumed to begin with ``media_url``.  If the
        resultant file path is outside the media directory, then a ValueError
        is raised.
        """
        # Remove ``media_url``.
        relative_url = url[len(self.media_url[2]):]
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

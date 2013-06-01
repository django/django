from django.conf import settings
from django.core.handlers.fs import FSFilesHandler

from django.contrib.staticfiles import utils
from django.contrib.staticfiles.views import serve


class StaticFilesHandler(FSFilesHandler):
    """
    WSGI middleware that intercepts calls to the static files directory, as
    defined by the STATIC_URL setting, and serves those files.
    """

    def get_base_dir(self):
        return settings.STATIC_ROOT

    def get_base_url(self):
        utils.check_settings()
        return settings.STATIC_URL

    def serve(self, request):
        """
        Actually serves the request path.
        """
        return serve(request, self.file_path(request.path), insecure=True)

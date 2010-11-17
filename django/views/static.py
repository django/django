"""
Views and functions for serving static files. These are only to be used
during development, and SHOULD NOT be used in a production setting.
"""

import mimetypes
import os
import posixpath
import re
import stat
import urllib
import warnings
from email.Utils import parsedate_tz, mktime_tz

from django.template import loader
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseNotModified
from django.template import Template, Context, TemplateDoesNotExist
from django.utils.http import http_date

from django.contrib.staticfiles.views import (directory_index,
    was_modified_since, serve as staticfiles_serve)


def serve(request, path, document_root=None, show_indexes=False, insecure=False):
    """
    Serve static files below a given point in the directory structure.

    To use, put a URL pattern such as::

        (r'^(?P<path>.*)$', 'django.views.static.serve', {'document_root' : '/path/to/my/files/'})

    in your URLconf. You must provide the ``document_root`` param. You may
    also set ``show_indexes`` to ``True`` if you'd like to serve a basic index
    of the directory.  This index view will use the template hardcoded below,
    but if you'd like to override it, you can create a template called
    ``static/directory_index.html``.
    """
    warnings.warn("The view at `django.views.static.serve` is deprecated; "
                  "use the path `django.contrib.staticfiles.views.serve` "
                  "instead.", PendingDeprecationWarning)
    return staticfiles_serve(request, path, document_root, show_indexes, insecure)

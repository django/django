import os
import urllib
import posixpath
import mimetypes
from django.core import template_loader
from django.core.exceptions import Http404, ImproperlyConfigured
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.core.template import Template, Context, TemplateDoesNotExist

def serve(request, path, document_root=None, show_indexes=False):
    """
    Serve static files below a given point in the directory structure.

    To use, put a URL pattern such as::

        (r'^(?P<path>.*)$', 'django.views.static.serve', {'document_root' : '/path/to/my/files/'})

    in your URLconf. You must provide the ``document_root`` param. You may
    also set ``show_indexes`` to ``True`` if you'd like to serve a basic index
    of the directory.  This index view will use the template hardcoded below,
    but if you'd like to override it, you can create a template called
    ``static/directory_index``.
    """

    # Clean up given path to only allow serving files below document_root.
    path = posixpath.normpath(urllib.unquote(path))
    newpath = ''
    for part in path.split('/'):
        if not part:
            # strip empty path components
            continue
        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # strip '.' amd '..' in path
            continue
        newpath = os.path.join(newpath, part).replace('\\', '/')
    if newpath and path != newpath:
        return HttpResponseRedirect(newpath)
    fullpath = os.path.join(document_root, newpath)
    if os.path.isdir(fullpath):
        if show_indexes:
            return directory_index(newpath, fullpath)
        else:
            raise Http404, "Directory indexes are not allowed here."
    elif not os.path.exists(fullpath):
        raise Http404, '"%s" does not exist' % fullpath
    else:
        mimetype = mimetypes.guess_type(fullpath)[0]
        return HttpResponse(open(fullpath, 'rb').read(), mimetype=mimetype)

DEFAULT_DIRECTORY_INDEX_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="Content-Language" content="en-us" />
    <meta name="robots" content="NONE,NOARCHIVE" />
    <title>Index of {{ directory }}</title>
  </head>
  <body>
    <h1>Index of {{ directory }}</h1>
    <ul>
      {% for f in file_list %}
      <li><a href="{{ f }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
  </body>
</html>
"""

def directory_index(path, fullpath):
    try:
        t = template_loader.get_template('static/directory_index')
    except TemplateDoesNotExist:
        t = Template(DEFAULT_DIRECTORY_INDEX_TEMPLATE)
    files = []
    for f in os.listdir(fullpath):
        if not f.startswith('.'):
            if os.path.isdir(os.path.join(fullpath, f)):
                f += '/'
            files.append(f)
    c = Context({
        'directory' : path + '/',
        'file_list' : files,
    })
    return HttpResponse(t.render(c))

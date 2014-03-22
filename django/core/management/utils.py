from __future__ import absolute_import

import os
from subprocess import PIPE, Popen
import sys

from django.utils.encoding import force_text, DEFAULT_LOCALE_ENCODING
from django.utils import six

from .base import CommandError


def popen_wrapper(args, os_err_exc_type=CommandError):
    """
    Friendly wrapper around Popen.

    Returns stdout output, stderr output and OS status code.
    """
    try:
        p = Popen(args, shell=False, stdout=PIPE, stderr=PIPE,
                close_fds=os.name != 'nt', universal_newlines=True)
    except OSError as e:
        six.reraise(os_err_exc_type, os_err_exc_type('Error executing %s: %s' %
                    (args[0], e.strerror)), sys.exc_info()[2])
    output, errors = p.communicate()
    return (
        output,
        force_text(errors, DEFAULT_LOCALE_ENCODING, strings_only=True),
        p.returncode
    )


def handle_extensions(extensions=('html',), ignored=('py',)):
    """
    Organizes multiple extensions that are separated with commas or passed by
    using --extension/-e multiple times. Note that the .py extension is ignored
    here because of the way non-*.py files are handled in make_messages() (they
    are copied to file.ext.py files to trick xgettext to parse them as Python
    files).

    For example: running 'django-admin makemessages -e js,txt -e xhtml -a'
    would result in an extension list: ['.js', '.txt', '.xhtml']

    >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
    set(['.html', '.js'])
    >>> handle_extensions(['.html, txt,.tpl'])
    set(['.html', '.tpl', '.txt'])
    """
    ext_list = []
    for ext in extensions:
        ext_list.extend(ext.replace(' ', '').split(','))
    for i, ext in enumerate(ext_list):
        if not ext.startswith('.'):
            ext_list[i] = '.%s' % ext_list[i]
    return set([x for x in ext_list if x.strip('.') not in ignored])

def find_command(cmd, path=None, pathext=None):
    if path is None:
        path = os.environ.get('PATH', '').split(os.pathsep)
    if isinstance(path, six.string_types):
        path = [path]
    # check if there are funny path extensions for executables, e.g. Windows
    if pathext is None:
        pathext = os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD').split(os.pathsep)
    # don't use extensions if the command ends with one of them
    for ext in pathext:
        if cmd.endswith(ext):
            pathext = ['']
            break
    # check if we find the command on PATH
    for p in path:
        f = os.path.join(p, cmd)
        if os.path.isfile(f):
            return f
        for ext in pathext:
            fext = f + ext
            if os.path.isfile(fext):
                return fext
    return None

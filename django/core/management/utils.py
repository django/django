from __future__ import unicode_literals

import os
import sys
from subprocess import PIPE, Popen

from django.apps import apps as installed_apps
from django.utils import six
from django.utils.crypto import get_random_string
from django.utils.encoding import DEFAULT_LOCALE_ENCODING, force_text

from .base import CommandError


def popen_wrapper(args, os_err_exc_type=CommandError, stdout_encoding='utf-8'):
    """
    Friendly wrapper around Popen.

    Returns stdout output, stderr output and OS status code.
    """
    try:
        p = Popen(args, shell=False, stdout=PIPE, stderr=PIPE, close_fds=os.name != 'nt')
    except OSError as e:
        strerror = force_text(e.strerror, DEFAULT_LOCALE_ENCODING, strings_only=True)
        six.reraise(os_err_exc_type, os_err_exc_type('Error executing %s: %s' %
                    (args[0], strerror)), sys.exc_info()[2])
    output, errors = p.communicate()
    return (
        force_text(output, stdout_encoding, strings_only=True, errors='strict'),
        force_text(errors, DEFAULT_LOCALE_ENCODING, strings_only=True, errors='replace'),
        p.returncode
    )


def handle_extensions(extensions):
    """
    Organizes multiple extensions that are separated with commas or passed by
    using --extension/-e multiple times.

    For example: running 'django-admin makemessages -e js,txt -e xhtml -a'
    would result in an extension list: ['.js', '.txt', '.xhtml']

    >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
    {'.html', '.js', '.py'}
    >>> handle_extensions(['.html, txt,.tpl'])
    {'.html', '.tpl', '.txt'}
    """
    ext_list = []
    for ext in extensions:
        ext_list.extend(ext.replace(' ', '').split(','))
    for i, ext in enumerate(ext_list):
        if not ext.startswith('.'):
            ext_list[i] = '.%s' % ext_list[i]
    return set(ext_list)


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


def get_random_secret_key():
    """
    Return a 50 character random string usable as a SECRET_KEY setting value.
    """
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return get_random_string(50, chars)


def parse_apps_and_model_labels(labels):
    """
    Parse a list of "app_label.ModelName" or "app_label" strings into actual
    objects and return a two-element tuple:
        (set of model classes, set of app_configs).
    Raise a CommandError if some specified models or apps don't exist.
    """
    apps = set()
    models = set()

    for label in labels:
        if '.' in label:
            try:
                model = installed_apps.get_model(label)
            except LookupError:
                raise CommandError('Unknown model: %s' % label)
            models.add(model)
        else:
            try:
                app_config = installed_apps.get_app_config(label)
            except LookupError as e:
                raise CommandError(str(e))
            apps.add(app_config)

    return models, apps

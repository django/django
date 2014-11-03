from __future__ import print_function

import sys
import time

import gunicorn.app.base as gapp
import gunicorn.glogging as glogging

from django.core.management.color import color_style
from django.utils import six

__all__ = ['GunicornApplication', 'get_gunicorn_config']


def get_gunicorn_config(**options):
    return {
        'bind': '{:s}:{:d}'.format(*options.get('bind')),
        'reload': options.get('reload'),
        'worker_class': 'sync',
        'accesslog': '-',
        'errorlog': '-',
        'access_log_format': '%(t)s"%(r)s" %(s)s %(b)s',
        'logger_class': 'django.core.servers.gserver.DjangoLogger',
    }


class GunicornApplication(gapp.Application):

    def __init__(self, options=None):
        self.options = options or {}
        super(GunicornApplication, self).__init__()

    def load_config(self):
        normalize_config = {key.lower(): value
                            for key, value in six.iteritems(self.options)}
        config = {key: value
                  for key, value in six.iteritems(normalize_config)
                  if key in self.cfg.settings and value is not None}
        for key, value in six.iteritems(config):
            self.cfg.set(key, value)

    def load(self):
        from django.core.servers.basehttp import get_internal_wsgi_application
        return get_internal_wsgi_application()


class DjangoLogger(glogging.Logger):

    datefmt = r"[%d/%b/%Y %H:%M:%S]"

    def __init__(self, cfg):
        self.style = color_style()
        super(DjangoLogger, self).__init__(cfg)

    def now(self):
        return time.strftime('[%d/%b/%Y %H:%M:%S]')

    def atoms(self, resp, req, environ, request_time):
        atoms = super(DjangoLogger, self).atoms(resp, req, environ, request_time)
        # stock django http server prints "0" instead of "-" when response
        # length is 0
        atoms['b'] = resp.response_length or '0'
        return atoms

    def access(self, resp, req, environ, request_time):
        if not self.cfg.accesslog and not self.cfg.logconfig:
            return

        safe_atoms = self.atoms_wrapper_class(self.atoms(resp, req, environ, request_time))

        msg = self.cfg.access_log_format % safe_atoms
        status = resp.status.split(None, 1)[0]

        if status[0] == '2':
            # Put 2XX first, since it should be the common case
            msg = self.style.HTTP_SUCCESS(msg)
        elif status[0] == '1':
            msg = self.style.HTTP_INFO(msg)
        elif status == '304':
            msg = self.style.HTTP_NOT_MODIFIED(msg)
        elif status[0] == '3':
            msg = self.style.HTTP_REDIRECT(msg)
        elif status == '404':
            msg = self.style.HTTP_NOT_FOUND(msg)
        elif status[0] == '4':
            msg = self.style.HTTP_BAD_REQUEST(msg)
        else:
            # Any 5XX, or any other response
            msg = self.style.HTTP_SERVER_ERROR(msg)

        try:
            self.access_log.info(msg)
        except:
            self.error(traceback.format_exc())

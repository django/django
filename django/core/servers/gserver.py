import shlex
import sys
import time

import gunicorn.glogging as glogging

from django.core.management.color import color_style
from django.utils import six

__all__ = ['get_gunicorn_args']


def get_gunicorn_args(**options):
    config = """\
    {app_name}
    --bind {:s}:{:d}
    {reload}
    --access-logfile -
    --error-logfile -
    --access-logformat '%(t)s"%(r)s" %(s)s %(b)s'
    --logger-class django.core.servers.gserver.DjangoLogger
    """.format
    app_name = options.get('app_name')
    if ':' not in app_name:
        app_name = ':'.join(app_name.rsplit('.', 1))
    return shlex.split(config(
        *options.get('bind'),
        app_name=app_name,
        reload='--reload' if options.get('reload') else ''
    ))


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

import logging
import sys
from django.core import mail

# Make sure a NullHandler is available
# This was added in Python 2.7/3.2
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

# Make sure that dictConfig is available
# This was added in Python 2.7/3.2
try:
    from logging.config import dictConfig
except ImportError:
    from django.utils.dictconfig import dictConfig

if sys.version_info < (2, 5):
    class LoggerCompat(object):
        def __init__(self, logger):
            self._logger = logger

        def __getattr__(self, name):
            val = getattr(self._logger, name)
            if callable(val):
                def _wrapper(*args, **kwargs):
                    # Python 2.4 logging module doesn't support 'extra' parameter to
                    # methods of Logger
                    kwargs.pop('extra', None)
                    return val(*args, **kwargs)
                return _wrapper
            else:
                return val

    def getLogger(name=None):
        return LoggerCompat(logging.getLogger(name=name))
else:
    getLogger = logging.getLogger

# Ensure the creation of the Django logger
# with a null handler. This ensures we don't get any
# 'No handlers could be found for logger "django"' messages
logger = getLogger('django')
if not logger.handlers:
    logger.addHandler(NullHandler())

class AdminEmailHandler(logging.Handler):
    """An exception log handler that emails log entries to site admins

    If the request is passed as the first argument to the log record,
    request data will be provided in the
    """
    def emit(self, record):
        import traceback
        from django.conf import settings
        from django.views.debug import ExceptionReporter

        try:
            if sys.version_info < (2,5):
                # A nasty workaround required because Python 2.4's logging
                # module doesn't support passing in extra context.
                # For this handler, the only extra data we need is the
                # request, and that's in the top stack frame.
                request = record.exc_info[2].tb_frame.f_locals['request']
            else:
                request = record.request

            subject = '%s (%s IP): %s' % (
                record.levelname,
                (request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'),
                record.msg
            )
            request_repr = repr(request)
        except:
            subject = 'Error: Unknown URL'
            request = None
            request_repr = "Request repr() unavailable"

        if record.exc_info:
            exc_info = record.exc_info
            stack_trace = '\n'.join(traceback.format_exception(*record.exc_info))
        else:
            exc_info = ()
            stack_trace = 'No stack trace available'

        message = "%s\n\n%s" % (stack_trace, request_repr)
        reporter = ExceptionReporter(request, is_email=True, *exc_info)
        html_message = reporter.get_traceback_html()
        mail.mail_admins(subject, message, fail_silently=True,
                         html_message=html_message)

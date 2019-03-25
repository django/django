# -*- coding: utf-8 -*-
"""
    sphinx.util.logging
    ~~~~~~~~~~~~~~~~~~~

    Logging utility functions for Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

import logging
import logging.handlers
from collections import defaultdict
from contextlib import contextmanager

from docutils import nodes
from docutils.utils import get_source_line
from six import PY2, StringIO

from sphinx.errors import SphinxWarning
from sphinx.util.console import colorize

if False:
    # For type annotation
    from typing import Any, Dict, Generator, IO, List, Tuple, Type, Union  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.application import Sphinx  # NOQA


NAMESPACE = 'sphinx'
VERBOSE = 15

LEVEL_NAMES = defaultdict(lambda: logging.WARNING)  # type: Dict[str, int]
LEVEL_NAMES.update({
    'CRITICAL': logging.CRITICAL,
    'SEVERE': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'VERBOSE': VERBOSE,
    'DEBUG': logging.DEBUG,
})

VERBOSITY_MAP = defaultdict(lambda: 0)  # type: Dict[int, int]
VERBOSITY_MAP.update({
    0: logging.INFO,
    1: VERBOSE,
    2: logging.DEBUG,
})

COLOR_MAP = defaultdict(lambda: 'blue')  # type: Dict[int, unicode]
COLOR_MAP.update({
    logging.ERROR: 'darkred',
    logging.WARNING: 'red',
    logging.DEBUG: 'darkgray',
})


def getLogger(name):
    # type: (str) -> SphinxLoggerAdapter
    """Get logger wrapped by :class:`sphinx.util.logging.SphinxLoggerAdapter`.

    Sphinx logger always uses ``sphinx.*`` namespace to be independent from
    settings of root logger.  It ensures logging is consistent even if a
    third-party extension or imported application resets logger settings.

    Example usage::

        >>> from sphinx.util import logging
        >>> logger = logging.getLogger(__name__)
        >>> logger.info('Hello, this is an extension!')
        Hello, this is an extension!
    """
    # add sphinx prefix to name forcely
    logger = logging.getLogger(NAMESPACE + '.' + name)
    # Forcely enable logger
    logger.disabled = False
    # wrap logger by SphinxLoggerAdapter
    return SphinxLoggerAdapter(logger, {})


def convert_serializable(records):
    # type: (List[logging.LogRecord]) -> None
    """Convert LogRecord serializable."""
    for r in records:
        # extract arguments to a message and clear them
        r.msg = r.getMessage()
        r.args = ()

        location = getattr(r, 'location', None)
        if isinstance(location, nodes.Node):
            r.location = get_node_location(location)  # type: ignore


class SphinxLogRecord(logging.LogRecord):
    """Log record class supporting location"""
    prefix = ''
    location = None  # type: Any

    def getMessage(self):
        # type: () -> str
        message = super(SphinxLogRecord, self).getMessage()
        location = getattr(self, 'location', None)
        if location:
            message = '%s: %s%s' % (location, self.prefix, message)
        elif self.prefix not in message:
            message = self.prefix + message

        return message


class SphinxInfoLogRecord(SphinxLogRecord):
    """Info log record class supporting location"""
    prefix = ''  # do not show any prefix for INFO messages


class SphinxWarningLogRecord(SphinxLogRecord):
    """Warning log record class supporting location"""
    prefix = 'WARNING: '


class SphinxLoggerAdapter(logging.LoggerAdapter):
    """LoggerAdapter allowing ``type`` and ``subtype`` keywords."""

    def log(self, level, msg, *args, **kwargs):
        # type: (Union[int, str], unicode, Any, Any) -> None
        if isinstance(level, int):
            super(SphinxLoggerAdapter, self).log(level, msg, *args, **kwargs)
        else:
            levelno = LEVEL_NAMES[level]
            super(SphinxLoggerAdapter, self).log(levelno, msg, *args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        # type: (unicode, Any, Any) -> None
        self.log(VERBOSE, msg, *args, **kwargs)

    def process(self, msg, kwargs):  # type: ignore
        # type: (unicode, Dict) -> Tuple[unicode, Dict]
        extra = kwargs.setdefault('extra', {})
        if 'type' in kwargs:
            extra['type'] = kwargs.pop('type')
        if 'subtype' in kwargs:
            extra['subtype'] = kwargs.pop('subtype')
        if 'location' in kwargs:
            extra['location'] = kwargs.pop('location')
        if 'nonl' in kwargs:
            extra['nonl'] = kwargs.pop('nonl')
        if 'color' in kwargs:
            extra['color'] = kwargs.pop('color')

        return msg, kwargs

    def handle(self, record):
        # type: (logging.LogRecord) -> None
        self.logger.handle(record)


class WarningStreamHandler(logging.StreamHandler):
    """StreamHandler for warnings."""
    pass


class NewLineStreamHandlerPY2(logging.StreamHandler):
    """StreamHandler which switches line terminator by record.nonl flag."""

    def emit(self, record):
        # type: (logging.LogRecord) -> None
        try:
            self.acquire()
            stream = self.stream
            if getattr(record, 'nonl', False):
                # remove return code forcely when nonl=True
                self.stream = StringIO()
                super(NewLineStreamHandlerPY2, self).emit(record)
                stream.write(self.stream.getvalue()[:-1])
                stream.flush()
            else:
                super(NewLineStreamHandlerPY2, self).emit(record)
        finally:
            self.stream = stream
            self.release()


class NewLineStreamHandlerPY3(logging.StreamHandler):
    """StreamHandler which switches line terminator by record.nonl flag."""

    def emit(self, record):
        # type: (logging.LogRecord) -> None
        try:
            self.acquire()
            if getattr(record, 'nonl', False):
                # skip appending terminator when nonl=True
                self.terminator = ''
            super(NewLineStreamHandlerPY3, self).emit(record)
        finally:
            self.terminator = '\n'
            self.release()


if PY2:
    NewLineStreamHandler = NewLineStreamHandlerPY2
else:
    NewLineStreamHandler = NewLineStreamHandlerPY3


class MemoryHandler(logging.handlers.BufferingHandler):
    """Handler buffering all logs."""

    def __init__(self):
        # type: () -> None
        super(MemoryHandler, self).__init__(-1)

    def shouldFlush(self, record):
        # type: (logging.LogRecord) -> bool
        return False  # never flush

    def flushTo(self, logger):
        # type: (logging.Logger) -> None
        self.acquire()
        try:
            for record in self.buffer:
                logger.handle(record)
            self.buffer = []  # type: List[logging.LogRecord]
        finally:
            self.release()

    def clear(self):
        # type: () -> List[logging.LogRecord]
        buffer, self.buffer = self.buffer, []
        return buffer


@contextmanager
def pending_warnings():
    # type: () -> Generator
    """Contextmanager to pend logging warnings temporary.

    Similar to :func:`pending_logging`.
    """
    logger = logging.getLogger(NAMESPACE)
    memhandler = MemoryHandler()
    memhandler.setLevel(logging.WARNING)

    try:
        handlers = []
        for handler in logger.handlers[:]:
            if isinstance(handler, WarningStreamHandler):
                logger.removeHandler(handler)
                handlers.append(handler)

        logger.addHandler(memhandler)
        yield memhandler
    finally:
        logger.removeHandler(memhandler)

        for handler in handlers:
            logger.addHandler(handler)

        memhandler.flushTo(logger)


@contextmanager
def pending_logging():
    # type: () -> Generator
    """Contextmanager to pend logging all logs temporary.

    For example::

        >>> with pending_logging():
        >>>     logger.warning('Warning message!')  # not flushed yet
        >>>     some_long_process()
        >>>
        Warning message!  # the warning is flushed here
    """
    logger = logging.getLogger(NAMESPACE)
    memhandler = MemoryHandler()

    try:
        handlers = []
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handlers.append(handler)

        logger.addHandler(memhandler)
        yield memhandler
    finally:
        logger.removeHandler(memhandler)

        for handler in handlers:
            logger.addHandler(handler)

        memhandler.flushTo(logger)


@contextmanager
def skip_warningiserror(skip=True):
    # type: (bool) -> Generator
    """contextmanager to skip WarningIsErrorFilter for a while."""
    logger = logging.getLogger(NAMESPACE)

    if skip is False:
        yield
    else:
        try:
            disabler = DisableWarningIsErrorFilter()
            for handler in logger.handlers:
                # use internal method; filters.insert() directly to install disabler
                # before WarningIsErrorFilter
                handler.filters.insert(0, disabler)
            yield
        finally:
            for handler in logger.handlers:
                handler.removeFilter(disabler)


class LogCollector(object):
    def __init__(self):
        # type: () -> None
        self.logs = []  # type: List[logging.LogRecord]

    @contextmanager
    def collect(self):
        # type: () -> Generator
        with pending_logging() as memhandler:
            yield

            self.logs = memhandler.clear()


class InfoFilter(logging.Filter):
    """Filter error and warning messages."""

    def filter(self, record):
        # type: (logging.LogRecord) -> bool
        if record.levelno < logging.WARNING:
            return True
        else:
            return False


def is_suppressed_warning(type, subtype, suppress_warnings):
    # type: (unicode, unicode, List[unicode]) -> bool
    """Check the warning is suppressed or not."""
    if type is None:
        return False

    for warning_type in suppress_warnings:
        if '.' in warning_type:
            target, subtarget = warning_type.split('.', 1)
        else:
            target, subtarget = warning_type, None

        if target == type:
            if (subtype is None or subtarget is None or
               subtarget == subtype or subtarget == '*'):
                return True

    return False


class WarningSuppressor(logging.Filter):
    """Filter logs by `suppress_warnings`."""

    def __init__(self, app):
        # type: (Sphinx) -> None
        self.app = app
        super(WarningSuppressor, self).__init__()

    def filter(self, record):
        # type: (logging.LogRecord) -> bool
        type = getattr(record, 'type', None)
        subtype = getattr(record, 'subtype', None)

        try:
            suppress_warnings = self.app.config.suppress_warnings
        except AttributeError:
            # config is not initialized yet (ex. in conf.py)
            suppress_warnings = []

        if is_suppressed_warning(type, subtype, suppress_warnings):
            return False
        else:
            self.app._warncount += 1
            return True


class WarningIsErrorFilter(logging.Filter):
    """Raise exception if warning emitted."""

    def __init__(self, app):
        # type: (Sphinx) -> None
        self.app = app
        super(WarningIsErrorFilter, self).__init__()

    def filter(self, record):
        # type: (logging.LogRecord) -> bool
        if getattr(record, 'skip_warningsiserror', False):
            # disabled by DisableWarningIsErrorFilter
            return True
        elif self.app.warningiserror:
            location = getattr(record, 'location', '')
            try:
                message = record.msg % record.args
            except (TypeError, ValueError):
                message = record.msg  # use record.msg itself

            if location:
                raise SphinxWarning(location + ":" + message)
            else:
                raise SphinxWarning(message)
        else:
            return True


class DisableWarningIsErrorFilter(logging.Filter):
    """Disable WarningIsErrorFilter if this filter installed."""

    def filter(self, record):
        # type: (logging.LogRecord) -> bool
        record.skip_warningsiserror = True  # type: ignore
        return True


class SphinxLogRecordTranslator(logging.Filter):
    """Converts a log record to one Sphinx expects

    * Make a instance of SphinxLogRecord
    * docname to path if location given
    """
    LogRecordClass = None  # type: Type[logging.LogRecord]

    def __init__(self, app):
        # type: (Sphinx) -> None
        self.app = app
        super(SphinxLogRecordTranslator, self).__init__()

    def filter(self, record):  # type: ignore
        # type: (SphinxWarningLogRecord) -> bool
        if isinstance(record, logging.LogRecord):
            # force subclassing to handle location
            record.__class__ = self.LogRecordClass  # type: ignore

        location = getattr(record, 'location', None)
        if isinstance(location, tuple):
            docname, lineno = location
            if docname and lineno:
                record.location = '%s:%s' % (self.app.env.doc2path(docname), lineno)
            elif docname:
                record.location = '%s' % self.app.env.doc2path(docname)
            else:
                record.location = None
        elif isinstance(location, nodes.Node):
            record.location = get_node_location(location)
        elif location and ':' not in location:
            record.location = '%s' % self.app.env.doc2path(location)

        return True


class InfoLogRecordTranslator(SphinxLogRecordTranslator):
    """LogRecordTranslator for INFO level log records."""
    LogRecordClass = SphinxInfoLogRecord


class WarningLogRecordTranslator(SphinxLogRecordTranslator):
    """LogRecordTranslator for WARNING level log records."""
    LogRecordClass = SphinxWarningLogRecord


def get_node_location(node):
    # type: (nodes.Node) -> str
    (source, line) = get_source_line(node)
    if source and line:
        return "%s:%s" % (source, line)
    elif source:
        return "%s:" % source
    elif line:
        return "<unknown>:%s" % line
    else:
        return None


class ColorizeFormatter(logging.Formatter):
    def format(self, record):
        # type: (logging.LogRecord) -> str
        message = super(ColorizeFormatter, self).format(record)
        color = getattr(record, 'color', None)
        if color is None:
            color = COLOR_MAP.get(record.levelno)

        if color:
            return colorize(color, message)  # type: ignore
        else:
            return message


class SafeEncodingWriter(object):
    """Stream writer which ignores UnicodeEncodeError silently"""
    def __init__(self, stream):
        # type: (IO) -> None
        self.stream = stream
        self.encoding = getattr(stream, 'encoding', 'ascii') or 'ascii'

    def write(self, data):
        # type: (unicode) -> None
        try:
            self.stream.write(data)
        except UnicodeEncodeError:
            # stream accept only str, not bytes.  So, we encode and replace
            # non-encodable characters, then decode them.
            self.stream.write(data.encode(self.encoding, 'replace').decode(self.encoding))

    def flush(self):
        # type: () -> None
        if hasattr(self.stream, 'flush'):
            self.stream.flush()


class LastMessagesWriter(object):
    """Stream writer which memories last 10 messages to save trackback"""
    def __init__(self, app, stream):
        # type: (Sphinx, IO) -> None
        self.app = app

    def write(self, data):
        # type: (unicode) -> None
        self.app.messagelog.append(data)


def setup(app, status, warning):
    # type: (Sphinx, IO, IO) -> None
    """Setup root logger for Sphinx"""
    logger = logging.getLogger(NAMESPACE)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # clear all handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    info_handler = NewLineStreamHandler(SafeEncodingWriter(status))  # type: ignore
    info_handler.addFilter(InfoFilter())
    info_handler.addFilter(InfoLogRecordTranslator(app))
    info_handler.setLevel(VERBOSITY_MAP[app.verbosity])
    info_handler.setFormatter(ColorizeFormatter())

    warning_handler = WarningStreamHandler(SafeEncodingWriter(warning))  # type: ignore
    warning_handler.addFilter(WarningSuppressor(app))
    warning_handler.addFilter(WarningLogRecordTranslator(app))
    warning_handler.addFilter(WarningIsErrorFilter(app))
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(ColorizeFormatter())

    messagelog_handler = logging.StreamHandler(LastMessagesWriter(app, status))  # type: ignore
    messagelog_handler.addFilter(InfoFilter())
    messagelog_handler.setLevel(VERBOSITY_MAP[app.verbosity])
    messagelog_handler.setFormatter(ColorizeFormatter())

    logger.addHandler(info_handler)
    logger.addHandler(warning_handler)
    logger.addHandler(messagelog_handler)

"""Logging utility functions for Sphinx."""

from __future__ import annotations

import logging
import logging.handlers
from collections import defaultdict
from contextlib import contextmanager
from typing import IO, TYPE_CHECKING, Any

from docutils import nodes
from docutils.utils import get_source_line

from sphinx.errors import SphinxWarning
from sphinx.util.console import colorize
from sphinx.util.osutil import abspath

if TYPE_CHECKING:
    from collections.abc import Generator

    from docutils.nodes import Node

    from sphinx.application import Sphinx


NAMESPACE = 'sphinx'
VERBOSE = 15

LEVEL_NAMES: defaultdict[str, int] = defaultdict(lambda: logging.WARNING, {
    'CRITICAL': logging.CRITICAL,
    'SEVERE': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'VERBOSE': VERBOSE,
    'DEBUG': logging.DEBUG,
})

VERBOSITY_MAP: defaultdict[int, int] = defaultdict(lambda: logging.NOTSET, {
    0: logging.INFO,
    1: VERBOSE,
    2: logging.DEBUG,
})

COLOR_MAP: defaultdict[int, str] = defaultdict(lambda: 'blue', {
    logging.ERROR: 'darkred',
    logging.WARNING: 'red',
    logging.DEBUG: 'darkgray',
})


def getLogger(name: str) -> SphinxLoggerAdapter:
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


def convert_serializable(records: list[logging.LogRecord]) -> None:
    """Convert LogRecord serializable."""
    for r in records:
        # extract arguments to a message and clear them
        r.msg = r.getMessage()
        r.args = ()

        location = getattr(r, 'location', None)
        if isinstance(location, nodes.Node):
            r.location = get_node_location(location)


class SphinxLogRecord(logging.LogRecord):
    """Log record class supporting location"""
    prefix = ''
    location: Any = None

    def getMessage(self) -> str:
        message = super().getMessage()
        location = getattr(self, 'location', None)
        if location:
            message = f'{location}: {self.prefix}{message}'
        elif self.prefix not in message:
            message = self.prefix + message

        return message


class SphinxInfoLogRecord(SphinxLogRecord):
    """Info log record class supporting location"""
    prefix = ''  # do not show any prefix for INFO messages


class SphinxWarningLogRecord(SphinxLogRecord):
    """Warning log record class supporting location"""
    @property
    def prefix(self) -> str:  # type: ignore[override]
        if self.levelno >= logging.CRITICAL:
            return 'CRITICAL: '
        elif self.levelno >= logging.ERROR:
            return 'ERROR: '
        else:
            return 'WARNING: '


class SphinxLoggerAdapter(logging.LoggerAdapter):
    """LoggerAdapter allowing ``type`` and ``subtype`` keywords."""
    KEYWORDS = ['type', 'subtype', 'location', 'nonl', 'color', 'once']

    def log(  # type: ignore[override]
        self, level: int | str, msg: str, *args: Any, **kwargs: Any,
    ) -> None:
        if isinstance(level, int):
            super().log(level, msg, *args, **kwargs)
        else:
            levelno = LEVEL_NAMES[level]
            super().log(levelno, msg, *args, **kwargs)

    def verbose(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(VERBOSE, msg, *args, **kwargs)

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:  # type: ignore[override]
        extra = kwargs.setdefault('extra', {})
        for keyword in self.KEYWORDS:
            if keyword in kwargs:
                extra[keyword] = kwargs.pop(keyword)

        return msg, kwargs

    def handle(self, record: logging.LogRecord) -> None:
        self.logger.handle(record)


class WarningStreamHandler(logging.StreamHandler):
    """StreamHandler for warnings."""
    pass


class NewLineStreamHandler(logging.StreamHandler):
    """StreamHandler which switches line terminator by record.nonl flag."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.acquire()
            if getattr(record, 'nonl', False):
                # skip appending terminator when nonl=True
                self.terminator = ''
            super().emit(record)
        finally:
            self.terminator = '\n'
            self.release()


class MemoryHandler(logging.handlers.BufferingHandler):
    """Handler buffering all logs."""

    buffer: list[logging.LogRecord]

    def __init__(self) -> None:
        super().__init__(-1)

    def shouldFlush(self, record: logging.LogRecord) -> bool:
        return False  # never flush

    def flush(self) -> None:
        # suppress any flushes triggered by importing packages that flush
        # all handlers at initialization time
        pass

    def flushTo(self, logger: logging.Logger) -> None:
        self.acquire()
        try:
            for record in self.buffer:
                logger.handle(record)
            self.buffer = []
        finally:
            self.release()

    def clear(self) -> list[logging.LogRecord]:
        buffer, self.buffer = self.buffer, []
        return buffer


@contextmanager
def pending_warnings() -> Generator[logging.Handler, None, None]:
    """Context manager to postpone logging warnings temporarily.

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
def suppress_logging() -> Generator[MemoryHandler, None, None]:
    """Context manager to suppress logging all logs temporarily.

    For example::

        >>> with suppress_logging():
        >>>     logger.warning('Warning message!')  # suppressed
        >>>     some_long_process()
        >>>
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


@contextmanager
def pending_logging() -> Generator[MemoryHandler, None, None]:
    """Context manager to postpone logging all logs temporarily.

    For example::

        >>> with pending_logging():
        >>>     logger.warning('Warning message!')  # not flushed yet
        >>>     some_long_process()
        >>>
        Warning message!  # the warning is flushed here
    """
    logger = logging.getLogger(NAMESPACE)
    try:
        with suppress_logging() as memhandler:
            yield memhandler
    finally:
        memhandler.flushTo(logger)


@contextmanager
def skip_warningiserror(skip: bool = True) -> Generator[None, None, None]:
    """Context manager to skip WarningIsErrorFilter temporarily."""
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


@contextmanager
def prefixed_warnings(prefix: str) -> Generator[None, None, None]:
    """Context manager to prepend prefix to all warning log records temporarily.

    For example::

        >>> with prefixed_warnings("prefix:"):
        >>>     logger.warning('Warning message!')  # => prefix: Warning message!

    .. versionadded:: 2.0
    """
    logger = logging.getLogger(NAMESPACE)
    warning_handler = None
    for handler in logger.handlers:
        if isinstance(handler, WarningStreamHandler):
            warning_handler = handler
            break
    else:
        # warning stream not found
        yield
        return

    prefix_filter = None
    for _filter in warning_handler.filters:
        if isinstance(_filter, MessagePrefixFilter):
            prefix_filter = _filter
            break

    if prefix_filter:
        # already prefixed
        try:
            previous = prefix_filter.prefix
            prefix_filter.prefix = prefix
            yield
        finally:
            prefix_filter.prefix = previous
    else:
        # not prefixed yet
        prefix_filter = MessagePrefixFilter(prefix)
        try:
            warning_handler.addFilter(prefix_filter)
            yield
        finally:
            warning_handler.removeFilter(prefix_filter)


class LogCollector:
    def __init__(self) -> None:
        self.logs: list[logging.LogRecord] = []

    @contextmanager
    def collect(self) -> Generator[None, None, None]:
        with pending_logging() as memhandler:
            yield

            self.logs = memhandler.clear()


class InfoFilter(logging.Filter):
    """Filter error and warning messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.WARNING


def is_suppressed_warning(type: str, subtype: str, suppress_warnings: list[str]) -> bool:
    """Check whether the warning is suppressed or not."""
    if type is None:
        return False

    subtarget: str | None

    for warning_type in suppress_warnings:
        if '.' in warning_type:
            target, subtarget = warning_type.split('.', 1)
        else:
            target, subtarget = warning_type, None

        if target == type and subtarget in (None, subtype, "*"):
            return True

    return False


class WarningSuppressor(logging.Filter):
    """Filter logs by `suppress_warnings`."""

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        type = getattr(record, 'type', '')
        subtype = getattr(record, 'subtype', '')

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

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
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
                exc = SphinxWarning(location + ":" + str(message))
            else:
                exc = SphinxWarning(message)
            if record.exc_info is not None:
                raise exc from record.exc_info[1]
            else:
                raise exc
        else:
            return True


class DisableWarningIsErrorFilter(logging.Filter):
    """Disable WarningIsErrorFilter if this filter installed."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.skip_warningsiserror = True
        return True


class MessagePrefixFilter(logging.Filter):
    """Prepend prefix to all log records."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        if self.prefix:
            record.msg = self.prefix + ' ' + record.msg
        return True


class OnceFilter(logging.Filter):
    """Show the message only once."""

    def __init__(self, name: str = '') -> None:
        super().__init__(name)
        self.messages: dict[str, list] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        once = getattr(record, 'once', '')
        if not once:
            return True
        else:
            params = self.messages.setdefault(record.msg, [])
            if record.args in params:
                return False

            params.append(record.args)
            return True


class SphinxLogRecordTranslator(logging.Filter):
    """Converts a log record to one Sphinx expects

    * Make a instance of SphinxLogRecord
    * docname to path if location given
    """
    LogRecordClass: type[logging.LogRecord]

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        super().__init__()

    def filter(self, record: SphinxWarningLogRecord) -> bool:  # type: ignore[override]
        if isinstance(record, logging.LogRecord):
            # force subclassing to handle location
            record.__class__ = self.LogRecordClass  # type: ignore[assignment]

        location = getattr(record, 'location', None)
        if isinstance(location, tuple):
            docname, lineno = location
            if docname:
                if lineno:
                    record.location = f'{self.app.env.doc2path(docname)}:{lineno}'
                else:
                    record.location = f'{self.app.env.doc2path(docname)}'
            else:
                record.location = None
        elif isinstance(location, nodes.Node):
            record.location = get_node_location(location)
        elif location and ':' not in location:
            record.location = f'{self.app.env.doc2path(location)}'

        return True


class InfoLogRecordTranslator(SphinxLogRecordTranslator):
    """LogRecordTranslator for INFO level log records."""
    LogRecordClass = SphinxInfoLogRecord


class WarningLogRecordTranslator(SphinxLogRecordTranslator):
    """LogRecordTranslator for WARNING level log records."""
    LogRecordClass = SphinxWarningLogRecord


def get_node_location(node: Node) -> str | None:
    source, line = get_source_line(node)
    if source:
        source = abspath(source)
    if source and line:
        return f"{source}:{line}"
    if source:
        return f"{source}:"
    if line:
        return f"<unknown>:{line}"
    return None


class ColorizeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = getattr(record, 'color', None)
        if color is None:
            color = COLOR_MAP.get(record.levelno)

        if color:
            return colorize(color, message)
        else:
            return message


class SafeEncodingWriter:
    """Stream writer which ignores UnicodeEncodeError silently"""
    def __init__(self, stream: IO) -> None:
        self.stream = stream
        self.encoding = getattr(stream, 'encoding', 'ascii') or 'ascii'

    def write(self, data: str) -> None:
        try:
            self.stream.write(data)
        except UnicodeEncodeError:
            # stream accept only str, not bytes.  So, we encode and replace
            # non-encodable characters, then decode them.
            self.stream.write(data.encode(self.encoding, 'replace').decode(self.encoding))

    def flush(self) -> None:
        if hasattr(self.stream, 'flush'):
            self.stream.flush()


class LastMessagesWriter:
    """Stream writer storing last 10 messages in memory to save trackback"""
    def __init__(self, app: Sphinx, stream: IO) -> None:
        self.app = app

    def write(self, data: str) -> None:
        self.app.messagelog.append(data)


def setup(app: Sphinx, status: IO, warning: IO) -> None:
    """Setup root logger for Sphinx"""
    logger = logging.getLogger(NAMESPACE)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # clear all handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    info_handler = NewLineStreamHandler(SafeEncodingWriter(status))
    info_handler.addFilter(InfoFilter())
    info_handler.addFilter(InfoLogRecordTranslator(app))
    info_handler.setLevel(VERBOSITY_MAP[app.verbosity])
    info_handler.setFormatter(ColorizeFormatter())

    warning_handler = WarningStreamHandler(SafeEncodingWriter(warning))
    warning_handler.addFilter(WarningSuppressor(app))
    warning_handler.addFilter(WarningLogRecordTranslator(app))
    warning_handler.addFilter(WarningIsErrorFilter(app))
    warning_handler.addFilter(OnceFilter())
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(ColorizeFormatter())

    messagelog_handler = logging.StreamHandler(LastMessagesWriter(app, status))
    messagelog_handler.addFilter(InfoFilter())
    messagelog_handler.setLevel(VERBOSITY_MAP[app.verbosity])

    logger.addHandler(info_handler)
    logger.addHandler(warning_handler)
    logger.addHandler(messagelog_handler)

# $Id: io.py 8129 2017-06-27 14:55:22Z grubert $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
I/O classes provide a uniform API for low-level input and output.  Subclasses
exist for a variety of input/output mechanisms.
"""

__docformat__ = 'reStructuredText'

import sys
import os
import re
import codecs
from docutils import TransformSpec
from docutils._compat import b
from docutils.utils.error_reporting import locale_encoding, ErrorString, ErrorOutput


class InputError(IOError): pass
class OutputError(IOError): pass

def check_encoding(stream, encoding):
    """Test, whether the encoding of `stream` matches `encoding`.

    Returns

    :None:  if `encoding` or `stream.encoding` are not a valid encoding
            argument (e.g. ``None``) or `stream.encoding is missing.
    :True:  if the encoding argument resolves to the same value as `encoding`,
    :False: if the encodings differ.
    """
    try:
        return codecs.lookup(stream.encoding) == codecs.lookup(encoding)
    except (LookupError, AttributeError, TypeError):
        return None


class Input(TransformSpec):

    """
    Abstract base class for input wrappers.
    """

    component_type = 'input'

    default_source_path = None

    def __init__(self, source=None, source_path=None, encoding=None,
                 error_handler='strict'):
        self.encoding = encoding
        """Text encoding for the input source."""

        self.error_handler = error_handler
        """Text decoding error handler."""

        self.source = source
        """The source of input data."""

        self.source_path = source_path
        """A text reference to the source."""

        if not source_path:
            self.source_path = self.default_source_path

        self.successful_encoding = None
        """The encoding that successfully decoded the source data."""

    def __repr__(self):
        return '%s: source=%r, source_path=%r' % (self.__class__, self.source,
                                                  self.source_path)

    def read(self):
        raise NotImplementedError

    def decode(self, data):
        """
        Decode a string, `data`, heuristically.
        Raise UnicodeError if unsuccessful.

        The client application should call ``locale.setlocale`` at the
        beginning of processing::

            locale.setlocale(locale.LC_ALL, '')
        """
        if self.encoding and self.encoding.lower() == 'unicode':
            assert isinstance(data, str), (
                'input encoding is "unicode" '
                'but input is not a unicode object')
        if isinstance(data, str):
            # Accept unicode even if self.encoding != 'unicode'.
            return data
        if self.encoding:
            # We believe the user/application when the encoding is
            # explicitly given.
            encodings = [self.encoding]
        else:
            data_encoding = self.determine_encoding_from_data(data)
            if data_encoding:
                # If the data declares its encoding (explicitly or via a BOM),
                # we believe it.
                encodings = [data_encoding]
            else:
                # Apply heuristics only if no encoding is explicitly given and
                # no BOM found.  Start with UTF-8, because that only matches
                # data that *IS* UTF-8:
                encodings = ['utf-8', 'latin-1']
                if locale_encoding:
                    encodings.insert(1, locale_encoding)
        for enc in encodings:
            try:
                decoded = str(data, enc, self.error_handler)
                self.successful_encoding = enc
                # Return decoded, removing BOMs.
                return decoded.replace('\ufeff', '')
            except (UnicodeError, LookupError) as err:
                error = err # in Python 3, the <exception instance> is
                            # local to the except clause
        raise UnicodeError(
            'Unable to decode input data.  Tried the following encodings: '
            '%s.\n(%s)' % (', '.join([repr(enc) for enc in encodings]),
                         ErrorString(error)))

    coding_slug = re.compile(b(r"coding[:=]\s*([-\w.]+)"))
    """Encoding declaration pattern."""

    byte_order_marks = ((codecs.BOM_UTF8, 'utf-8'), # 'utf-8-sig' new in v2.5
                        (codecs.BOM_UTF16_BE, 'utf-16-be'),
                        (codecs.BOM_UTF16_LE, 'utf-16-le'),)
    """Sequence of (start_bytes, encoding) tuples for encoding detection.
    The first bytes of input data are checked against the start_bytes strings.
    A match indicates the given encoding."""

    def determine_encoding_from_data(self, data):
        """
        Try to determine the encoding of `data` by looking *in* `data`.
        Check for a byte order mark (BOM) or an encoding declaration.
        """
        # check for a byte order mark:
        for start_bytes, encoding in self.byte_order_marks:
            if data.startswith(start_bytes):
                return encoding
        # check for an encoding declaration pattern in first 2 lines of file:
        for line in data.splitlines()[:2]:
            match = self.coding_slug.search(line)
            if match:
                return match.group(1).decode('ascii')
        return None


class Output(TransformSpec):

    """
    Abstract base class for output wrappers.
    """

    component_type = 'output'

    default_destination_path = None

    def __init__(self, destination=None, destination_path=None,
                 encoding=None, error_handler='strict'):
        self.encoding = encoding
        """Text encoding for the output destination."""

        self.error_handler = error_handler or 'strict'
        """Text encoding error handler."""

        self.destination = destination
        """The destination for output data."""

        self.destination_path = destination_path
        """A text reference to the destination."""

        if not destination_path:
            self.destination_path = self.default_destination_path

    def __repr__(self):
        return ('%s: destination=%r, destination_path=%r'
                % (self.__class__, self.destination, self.destination_path))

    def write(self, data):
        """`data` is a Unicode string, to be encoded by `self.encode`."""
        raise NotImplementedError

    def encode(self, data):
        if self.encoding and self.encoding.lower() == 'unicode':
            assert isinstance(data, str), (
                'the encoding given is "unicode" but the output is not '
                'a Unicode string')
            return data
        if not isinstance(data, str):
            # Non-unicode (e.g. bytes) output.
            return data
        else:
            return data.encode(self.encoding, self.error_handler)


class FileInput(Input):

    """
    Input for single, simple file-like objects.
    """
    def __init__(self, source=None, source_path=None,
                 encoding=None, error_handler='strict',
                 autoclose=True, mode='rU', **kwargs):
        """
        :Parameters:
            - `source`: either a file-like object (which is read directly), or
              `None` (which implies `sys.stdin` if no `source_path` given).
            - `source_path`: a path to a file, which is opened and then read.
            - `encoding`: the expected text encoding of the input file.
            - `error_handler`: the encoding error handler to use.
            - `autoclose`: close automatically after read (except when
              `sys.stdin` is the source).
            - `mode`: how the file is to be opened (see standard function
              `open`). The default 'rU' provides universal newline support
              for text files.
        """
        Input.__init__(self, source, source_path, encoding, error_handler)
        self.autoclose = autoclose
        self._stderr = ErrorOutput()
        # deprecation warning
        for key in kwargs:
            if key == 'handle_io_errors':
                sys.stderr.write('deprecation warning: '
                    'io.FileInput() argument `handle_io_errors` '
                    'is ignored since "Docutils 0.10 (2012-12-16)" '
                    'and will soon be removed.')
            else:
                raise TypeError('__init__() got an unexpected keyword '
                                "argument '%s'" % key)

        if source is None:
            if source_path:
                # Specify encoding in Python 3
                if sys.version_info >= (3,0):
                    kwargs = {'encoding': self.encoding,
                              'errors': self.error_handler}
                else:
                    kwargs = {}

                try:
                    self.source = open(source_path, mode, **kwargs)
                except IOError as error:
                    raise InputError(error.errno, error.strerror, source_path)
            else:
                self.source = sys.stdin
        elif (sys.version_info >= (3,0) and
              check_encoding(self.source, self.encoding) is False):
            # TODO: re-open, warn or raise error?
            raise UnicodeError('Encoding clash: encoding given is "%s" '
                               'but source is opened with encoding "%s".' %
                               (self.encoding, self.source.encoding))
        if not source_path:
            try:
                self.source_path = self.source.name
            except AttributeError:
                pass

    def read(self):
        """
        Read and decode a single file and return the data (Unicode string).
        """
        try: # In Python < 2.5, try...except has to be nested in try...finally.
            try:
                if self.source is sys.stdin and sys.version_info >= (3,0):
                    # read as binary data to circumvent auto-decoding
                    data = self.source.buffer.read()
                    # normalize newlines
                    data = b('\n').join(data.splitlines()) + b('\n')
                else:
                    data = self.source.read()
            except (UnicodeError, LookupError) as err: # (in Py3k read() decodes)
                if not self.encoding and self.source_path:
                    # re-read in binary mode and decode with heuristics
                    b_source = open(self.source_path, 'rb')
                    data = b_source.read()
                    b_source.close()
                    # normalize newlines
                    data = b('\n').join(data.splitlines()) + b('\n')
                else:
                    raise
        finally:
            if self.autoclose:
                self.close()
        return self.decode(data)

    def readlines(self):
        """
        Return lines of a single file as list of Unicode strings.
        """
        return self.read().splitlines(True)

    def close(self):
        if self.source is not sys.stdin:
            self.source.close()


class FileOutput(Output):

    """
    Output for single, simple file-like objects.
    """

    mode = 'w'
    """The mode argument for `open()`."""
    # 'wb' for binary (e.g. OpenOffice) files (see also `BinaryFileOutput`).
    # (Do not use binary mode ('wb') for text files, as this prevents the
    # conversion of newlines to the system specific default.)

    def __init__(self, destination=None, destination_path=None,
                 encoding=None, error_handler='strict', autoclose=True,
                 handle_io_errors=None, mode=None):
        """
        :Parameters:
            - `destination`: either a file-like object (which is written
              directly) or `None` (which implies `sys.stdout` if no
              `destination_path` given).
            - `destination_path`: a path to a file, which is opened and then
              written.
            - `encoding`: the text encoding of the output file.
            - `error_handler`: the encoding error handler to use.
            - `autoclose`: close automatically after write (except when
              `sys.stdout` or `sys.stderr` is the destination).
            - `handle_io_errors`: ignored, deprecated, will be removed.
            - `mode`: how the file is to be opened (see standard function
              `open`). The default is 'w', providing universal newline
              support for text files.
        """
        Output.__init__(self, destination, destination_path,
                        encoding, error_handler)
        self.opened = True
        self.autoclose = autoclose
        if mode is not None:
            self.mode = mode
        self._stderr = ErrorOutput()
        if destination is None:
            if destination_path:
                self.opened = False
            else:
                self.destination = sys.stdout
        elif (# destination is file-type object -> check mode:
              mode and hasattr(self.destination, 'mode')
              and mode != self.destination.mode):
                print(('Warning: Destination mode "%s" '
                               'differs from specified mode "%s"' %
                               (self.destination.mode, mode)), file=self._stderr)
        if not destination_path:
            try:
                self.destination_path = self.destination.name
            except AttributeError:
                pass

    def open(self):
        # Specify encoding in Python 3.
        if sys.version_info >= (3,0) and 'b' not in self.mode:
            kwargs = {'encoding': self.encoding,
                      'errors': self.error_handler}
        else:
            kwargs = {}
        try:
            self.destination = open(self.destination_path, self.mode, **kwargs)
        except IOError as error:
            raise OutputError(error.errno, error.strerror,
                              self.destination_path)
        self.opened = True

    def write(self, data):
        """Encode `data`, write it to a single file, and return it.

        With Python 3 or binary output mode, `data` is returned unchanged,
        except when specified encoding and output encoding differ.
        """
        if not self.opened:
            self.open()
        if ('b' not in self.mode and sys.version_info < (3,0)
            or check_encoding(self.destination, self.encoding) is False
           ):
            data = self.encode(data)
            if sys.version_info >= (3,0) and os.linesep != '\n':
                data = data.replace(b('\n'), b(os.linesep)) # fix endings

        try: # In Python < 2.5, try...except has to be nested in try...finally.
            try:
                self.destination.write(data)
            except TypeError as e:
                if sys.version_info >= (3,0) and isinstance(data, bytes):
                    try:
                        self.destination.buffer.write(data)
                    except AttributeError:
                        if check_encoding(self.destination,
                                          self.encoding) is False:
                            raise ValueError('Encoding of %s (%s) differs \n'
                                '  from specified encoding (%s)' %
                                (self.destination_path or 'destination',
                                self.destination.encoding, self.encoding))
                        else:
                            raise e
            except (UnicodeError, LookupError) as err:
                raise UnicodeError(
                    'Unable to encode output data. output-encoding is: '
                    '%s.\n(%s)' % (self.encoding, ErrorString(err)))
        finally:
            if self.autoclose:
                self.close()
        return data

    def close(self):
        if self.destination not in (sys.stdout, sys.stderr):
            self.destination.close()
            self.opened = False


class BinaryFileOutput(FileOutput):
    """
    A version of docutils.io.FileOutput which writes to a binary file.
    """
    # Used by core.publish_cmdline_to_binary() which in turn is used by
    # rst2odt (OpenOffice writer)
    mode = 'wb'


class StringInput(Input):

    """
    Direct string input.
    """

    default_source_path = '<string>'

    def read(self):
        """Decode and return the source string."""
        return self.decode(self.source)


class StringOutput(Output):

    """
    Direct string output.
    """

    default_destination_path = '<string>'

    def write(self, data):
        """Encode `data`, store it in `self.destination`, and return it."""
        self.destination = self.encode(data)
        return self.destination


class NullInput(Input):

    """
    Degenerate input: read nothing.
    """

    default_source_path = 'null input'

    def read(self):
        """Return a null string."""
        return ''


class NullOutput(Output):

    """
    Degenerate output: write nothing.
    """

    default_destination_path = 'null output'

    def write(self, data):
        """Do nothing ([don't even] send data to the bit bucket)."""
        pass


class DocTreeInput(Input):

    """
    Adapter for document tree input.

    The document tree must be passed in the ``source`` parameter.
    """

    default_source_path = 'doctree input'

    def read(self):
        """Return the document tree."""
        return self.source

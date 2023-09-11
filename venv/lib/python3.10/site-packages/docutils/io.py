# $Id: io.py 9369 2023-05-02 23:04:27Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
I/O classes provide a uniform API for low-level input and output.  Subclasses
exist for a variety of input/output mechanisms.
"""

__docformat__ = 'reStructuredText'

import codecs
import locale
import os
import re
import sys
import warnings

from docutils import TransformSpec


# Guess the locale's preferred encoding.
# If no valid guess can be made, _locale_encoding is set to `None`:
#
# TODO: check whether this is set correctly with every OS and Python version
#       or whether front-end tools need to call `locale.setlocale()`
#       before importing this module
try:
    # Return locale encoding also in UTF-8 mode
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _locale_encoding = (locale.getlocale()[1]
                            or locale.getdefaultlocale()[1])
        _locale_encoding = _locale_encoding.lower()
except ValueError as error:  # OS X may set UTF-8 without language code
    # See https://bugs.python.org/issue18378 fixed in 3.8
    # and https://sourceforge.net/p/docutils/bugs/298/.
    # Drop the special case after requiring Python >= 3.8
    if "unknown locale: UTF-8" in error.args:
        _locale_encoding = "utf-8"
    else:
        _locale_encoding = None
except:  # noqa  any other problems determining the locale -> use None
    _locale_encoding = None
try:
    codecs.lookup(_locale_encoding)
except (LookupError, TypeError):
    _locale_encoding = None


class InputError(OSError): pass
class OutputError(OSError): pass


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


def error_string(err):
    """Return string representation of Exception `err`.
    """
    return f'{err.__class__.__name__}: {err}'


class Input(TransformSpec):
    """
    Abstract base class for input wrappers.

    Docutils input objects must provide a `read()` method that
    returns the source, typically as `str` instance.

    Inheriting `TransformSpec` allows input objects to add
    "transforms" and "unknown_reference_resolvers" to the "Transformer".
    (Optional for custom input objects since Docutils 0.19.)
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
        """Return input as `str`. Define in subclasses."""
        raise NotImplementedError

    def decode(self, data):
        """
        Decode `data` if required.

        Return Unicode `str` instances unchanged (nothing to decode).

        If `self.encoding` is None, determine encoding from data
        or try UTF-8, locale encoding, and (as last ressort) 'latin-1'.
        The client application should call ``locale.setlocale`` at the
        beginning of processing::

            locale.setlocale(locale.LC_ALL, '')

        Raise UnicodeError if unsuccessful.

        Provisional:
          - Raise UnicodeError (instead of falling back to the locale
            encoding) if decoding the source with the default encoding (UTF-8)
            fails and Python is started in `UTF-8 mode`.

            Raise UnicodeError (instead of falling back to "latin1") if both,
            default and locale encoding, fail.

          - Only remove BOM (U+FEFF ZWNBSP at start of data),
            no other ZWNBSPs.
        """
        if self.encoding and self.encoding.lower() == 'unicode':
            assert isinstance(data, str), ('input encoding is "unicode" '
                                           'but `data` is no `str` instance')
        if isinstance(data, str):
            # nothing to decode
            return data
        if self.encoding:
            # We believe the user/application when the encoding is
            # explicitly given.
            encoding_candidates = [self.encoding]
        else:
            data_encoding = self.determine_encoding_from_data(data)
            if data_encoding:
                # If the data declares its encoding (explicitly or via a BOM),
                # we believe it.
                encoding_candidates = [data_encoding]
            else:
                # Apply heuristics only if no encoding is explicitly given and
                # no BOM found.  Start with UTF-8, because that only matches
                # data that *IS* UTF-8:
                encoding_candidates = ['utf-8']
                # TODO: use `locale.getpreferredlocale(do_setlocale=True)`
                # to respect UTF-8 mode (API change).
                # (Check if it is a valid encoding and not UTF-8)
                if _locale_encoding and _locale_encoding != 'utf-8':
                    encoding_candidates.append(_locale_encoding)
                # TODO: don't fall back to 'latin-1' (API change).
                encoding_candidates.append('latin-1')
        for enc in encoding_candidates:
            try:
                decoded = str(data, enc, self.error_handler)
                self.successful_encoding = enc
                # Return decoded, removing BOM and other ZWNBSPs.
                # TODO: only remove BOM (ZWNBSP at start of data)
                #       and only if 'self.encoding' is None. (API change)
                return decoded.replace('\ufeff', '')
            except (UnicodeError, LookupError) as err:
                # keep exception instance for use outside of the "for" loop.
                error = err
        raise UnicodeError(
            'Unable to decode input data.  Tried the following encodings: '
            f'{", ".join(repr(enc) for enc in encoding_candidates)}.\n'
            f'({error_string(error)})')

    coding_slug = re.compile(br"coding[:=]\s*([-\w.]+)")
    """Encoding declaration pattern."""

    byte_order_marks = ((codecs.BOM_UTF8, 'utf-8'),
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

    def isatty(self):
        """Return True, if the input source is connected to a TTY device."""
        try:
            return self.source.isatty()
        except AttributeError:
            return False


class Output(TransformSpec):
    """
    Abstract base class for output wrappers.

    Docutils output objects must provide a `write()` method that
    expects and handles one argument (the output).

    Inheriting `TransformSpec` allows output objects to add
    "transforms" and "unknown_reference_resolvers" to the "Transformer".
    (Optional for custom output objects since Docutils 0.19.)
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
        """Write `data`. Define in subclasses."""
        raise NotImplementedError

    def encode(self, data):
        """
        Encode and return `data`.

        If `data` is a `bytes` instance, it is returned unchanged.
        Otherwise it is encoded with `self.encoding`.

        Provisional: If `self.encoding` is set to the pseudo encoding name
        "unicode", `data` must be a `str` instance and is returned unchanged.
        """
        if self.encoding and self.encoding.lower() == 'unicode':
            assert isinstance(data, str), ('output encoding is "unicode" '
                                           'but `data` is no `str` instance')
            return data
        if not isinstance(data, str):
            # Non-unicode (e.g. bytes) output.
            return data
        else:
            return data.encode(self.encoding, self.error_handler)


class ErrorOutput:
    """
    Wrapper class for file-like error streams with
    failsafe de- and encoding of `str`, `bytes`, `unicode` and
    `Exception` instances.
    """

    def __init__(self, destination=None, encoding=None,
                 encoding_errors='backslashreplace',
                 decoding_errors='replace'):
        """
        :Parameters:
            - `destination`: a file-like object,
                        a string (path to a file),
                        `None` (write to `sys.stderr`, default), or
                        evaluating to `False` (write() requests are ignored).
            - `encoding`: `destination` text encoding. Guessed if None.
            - `encoding_errors`: how to treat encoding errors.
        """
        if destination is None:
            destination = sys.stderr
        elif not destination:
            destination = False
        # if `destination` is a file name, open it
        elif isinstance(destination, str):
            destination = open(destination, 'w')

        self.destination = destination
        """Where warning output is sent."""

        self.encoding = (encoding or getattr(destination, 'encoding', None)
                         or _locale_encoding or 'ascii')
        """The output character encoding."""

        self.encoding_errors = encoding_errors
        """Encoding error handler."""

        self.decoding_errors = decoding_errors
        """Decoding error handler."""

    def write(self, data):
        """
        Write `data` to self.destination. Ignore, if self.destination is False.

        `data` can be a `bytes`, `str`, or `Exception` instance.
        """
        if not self.destination:
            return
        if isinstance(data, Exception):
            data = str(data)
        try:
            self.destination.write(data)
        except UnicodeEncodeError:
            self.destination.write(data.encode(self.encoding,
                                               self.encoding_errors))
        except TypeError:
            if isinstance(data, str):  # destination may expect bytes
                self.destination.write(data.encode(self.encoding,
                                                   self.encoding_errors))
            elif self.destination in (sys.stderr, sys.stdout):
                # write bytes to raw stream
                self.destination.buffer.write(data)
            else:
                self.destination.write(str(data, self.encoding,
                                           self.decoding_errors))

    def close(self):
        """
        Close the error-output stream.

        Ignored if the destination is` sys.stderr` or `sys.stdout` or has no
        close() method.
        """
        if self.destination in (sys.stdout, sys.stderr):
            return
        try:
            self.destination.close()
        except AttributeError:
            pass

    def isatty(self):
        """Return True, if the destination is connected to a TTY device."""
        try:
            return self.destination.isatty()
        except AttributeError:
            return False


class FileInput(Input):

    """
    Input for single, simple file-like objects.
    """
    def __init__(self, source=None, source_path=None,
                 encoding=None, error_handler='strict',
                 autoclose=True, mode='r'):
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
              `open`). The default is read only ('r').
        """
        Input.__init__(self, source, source_path, encoding, error_handler)
        self.autoclose = autoclose
        self._stderr = ErrorOutput()

        if source is None:
            if source_path:
                try:
                    self.source = open(source_path, mode,
                                       encoding=self.encoding or 'utf-8-sig',
                                       errors=self.error_handler)
                except OSError as error:
                    raise InputError(error.errno, error.strerror, source_path)
            else:
                self.source = sys.stdin
        elif check_encoding(self.source, self.encoding) is False:
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
        try:
            if self.source is sys.stdin:
                # read as binary data to circumvent auto-decoding
                data = self.source.buffer.read()
            else:
                data = self.source.read()
        except (UnicodeError, LookupError):
            if not self.encoding and self.source_path:
                # re-read in binary mode and decode with heuristics
                b_source = open(self.source_path, 'rb')
                data = b_source.read()
                b_source.close()
            else:
                raise
        finally:
            if self.autoclose:
                self.close()
        data = self.decode(data)
        # normalise newlines
        return '\n'.join(data.splitlines()+[''])

    def readlines(self):
        """
        Return lines of a single file as list of Unicode strings.
        """
        return self.read().splitlines(True)

    def close(self):
        if self.source is not sys.stdin:
            self.source.close()


class FileOutput(Output):

    """Output for single, simple file-like objects."""

    default_destination_path = '<file>'

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
        if handle_io_errors is not None:
            warnings.warn('io.FileOutput: init argument "handle_io_errors" '
                          'is ignored and will be removed in '
                          'Docutils 2.0.', DeprecationWarning, stacklevel=2)
        if mode is not None:
            self.mode = mode
        self._stderr = ErrorOutput()
        if destination is None:
            if destination_path:
                self.opened = False
            else:
                self.destination = sys.stdout
        elif (  # destination is file-type object -> check mode:
              mode and hasattr(self.destination, 'mode')
              and mode != self.destination.mode):
            print('Warning: Destination mode "%s" differs from specified '
                  'mode "%s"' % (self.destination.mode, mode),
                  file=self._stderr)
        if not destination_path:
            try:
                self.destination_path = self.destination.name
            except AttributeError:
                pass

    def open(self):
        # Specify encoding
        if 'b' not in self.mode:
            kwargs = {'encoding': self.encoding,
                      'errors': self.error_handler}
        else:
            kwargs = {}
        try:
            self.destination = open(self.destination_path, self.mode, **kwargs)
        except OSError as error:
            raise OutputError(error.errno, error.strerror,
                              self.destination_path)
        self.opened = True

    def write(self, data):
        """Write `data` to a single file, also return it.

        `data` can be a `str` or `bytes` instance.
        If writing `bytes` fails, an attempt is made to write to
        the low-level interface ``self.destination.buffer``.

        If `data` is a `str` instance and `self.encoding` and
        `self.destination.encoding` are  set to different values, `data`
        is encoded to a `bytes` instance using `self.encoding`.

        Provisional: future versions may raise an error if `self.encoding`
        and `self.destination.encoding` are set to different values.
        """
        if not self.opened:
            self.open()
        if (isinstance(data, str)
            and check_encoding(self.destination, self.encoding) is False):
            if os.linesep != '\n':
                data = data.replace('\n', os.linesep)  # fix endings
            data = self.encode(data)

        try:
            self.destination.write(data)
        except TypeError as err:
            if isinstance(data, bytes):
                try:
                    self.destination.buffer.write(data)
                except AttributeError:
                    if check_encoding(self.destination,
                                      self.encoding) is False:
                        raise ValueError(
                            f'Encoding of {self.destination_path} '
                            f'({self.destination.encoding}) differs \n'
                            f'  from specified encoding ({self.encoding})')
                    else:
                        raise err
        except (UnicodeError, LookupError) as err:
            raise UnicodeError(
                'Unable to encode output data. output-encoding is: '
                f'{self.encoding}.\n({error_string(err)})')
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
    # tools/rst2odt.py but not by core.rst2odt().
    mode = 'wb'


class StringInput(Input):
    """Input from a `str` or `bytes` instance."""

    default_source_path = '<string>'

    def read(self):
        """Return the source as `str` instance.

        Decode, if required (see `Input.decode`).
        """
        return self.decode(self.source)


class StringOutput(Output):
    """Output to a `bytes` or `str` instance.

    Provisional.
    """

    default_destination_path = '<string>'

    def write(self, data):
        """Store `data` in `self.destination`, and return it.

        If `self.encoding` is set to the pseudo encoding name "unicode",
        `data` must be a `str` instance and is stored/returned unchanged
        (cf. `Output.encode`).

        Otherwise, `data` can be a `bytes` or `str` instance and is
        stored/returned as a `bytes` instance
        (`str` data is encoded with `self.encode()`).

        Attention: the `output_encoding`_ setting may affect the content
        of the output (e.g. an encoding declaration in HTML or XML or the
        representation of characters as LaTeX macro vs. literal character).
        """
        self.destination = self.encode(data)
        return self.destination


class NullInput(Input):

    """Degenerate input: read nothing."""

    default_source_path = 'null input'

    def read(self):
        """Return an empty string."""
        return ''


class NullOutput(Output):

    """Degenerate output: write nothing."""

    default_destination_path = 'null output'

    def write(self, data):
        """Do nothing, return None."""
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

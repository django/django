#!/usr/bin/env python
# -*- coding: utf-8 -*-

# :Id: $Id: error_reporting.py 8119 2017-06-22 20:59:19Z milde $
# :Copyright: © 2011 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: http://www.spdx.org/licenses/BSD-2-Clause

"""
Error reporting should be safe from encoding/decoding errors.
However, implicit conversions of strings and exceptions like

>>> u'%s world: %s' % ('H\xe4llo', Exception(u'H\xe4llo')

fail in some Python versions:

* In Python <= 2.6, ``unicode(<exception instance>)`` uses
  `__str__` and fails with non-ASCII chars in`unicode` arguments.
  (work around http://bugs.python.org/issue2517):

* In Python 2, unicode(<exception instance>) fails, with non-ASCII
  chars in arguments. (Use case: in some locales, the errstr
  argument of IOError contains non-ASCII chars.)

* In Python 2, str(<exception instance>) fails, with non-ASCII chars
  in `unicode` arguments.

The `SafeString`, `ErrorString` and `ErrorOutput` classes handle
common exceptions.
"""

import sys, codecs

# Guess the locale's encoding.
# If no valid guess can be made, locale_encoding is set to `None`:
try:
    import locale # module missing in Jython
except ImportError:
    locale_encoding = None
else:
    try:
        locale_encoding = locale.getlocale()[1] or locale.getdefaultlocale()[1]
        # locale.getpreferredencoding([do_setlocale=True|False])
        # has side-effects | might return a wrong guess.
        # (cf. Update 1 in http://stackoverflow.com/questions/4082645/using-python-2-xs-locale-module-to-format-numbers-and-currency)
    except ValueError as error: # OS X may set UTF-8 without language code
        # see http://bugs.python.org/issue18378
        # and https://sourceforge.net/p/docutils/bugs/298/
        if "unknown locale: UTF-8" in error.args:
            locale_encoding = "UTF-8"
        else:
            locale_encoding = None
    except: # any other problems determining the locale -> use None
        locale_encoding = None
    try:
        codecs.lookup(locale_encoding or '') # None -> ''
    except LookupError:
        locale_encoding = None



class SafeString(object):
    """
    A wrapper providing robust conversion to `str` and `unicode`.
    """

    def __init__(self, data, encoding=None, encoding_errors='backslashreplace',
                 decoding_errors='replace'):
        self.data = data
        self.encoding = (encoding or getattr(data, 'encoding', None) or
                         locale_encoding or 'ascii')
        self.encoding_errors = encoding_errors
        self.decoding_errors = decoding_errors


    def __str__(self):
        try:
            return str(self.data)
        except UnicodeEncodeError:
            if isinstance(self.data, Exception):
                args = [str(SafeString(arg, self.encoding,
                                        self.encoding_errors))
                        for arg in self.data.args]
                return ', '.join(args)
            if isinstance(self.data, str):
                if sys.version_info > (3,0):
                    return self.data
                else:
                    return self.data.encode(self.encoding,
                                            self.encoding_errors)
            raise

    def __unicode__(self):
        """
        Return unicode representation of `self.data`.

        Try ``unicode(self.data)``, catch `UnicodeError` and

        * if `self.data` is an Exception instance, work around
          http://bugs.python.org/issue2517 with an emulation of
          Exception.__unicode__,

        * else decode with `self.encoding` and `self.decoding_errors`.
        """
        try:
            u = str(self.data)
            if isinstance(self.data, EnvironmentError):
                u = u.replace(": u'", ": '") # normalize filename quoting
            return u
        except UnicodeError as error: # catch ..Encode.. and ..Decode.. errors
            if isinstance(self.data, EnvironmentError):
                return  "[Errno %s] %s: '%s'" % (self.data.errno,
                    SafeString(self.data.strerror, self.encoding,
                               self.decoding_errors),
                    SafeString(self.data.filename, self.encoding,
                               self.decoding_errors))
            if isinstance(self.data, Exception):
                args = [str(SafeString(arg, self.encoding,
                            decoding_errors=self.decoding_errors))
                        for arg in self.data.args]
                return ', '.join(args)
            if isinstance(error, UnicodeDecodeError):
                return str(self.data, self.encoding, self.decoding_errors)
            raise

class ErrorString(SafeString):
    """
    Safely report exception type and message.
    """
    def __str__(self):
        return '%s: %s' % (self.data.__class__.__name__,
                            super(ErrorString, self).__str__())

    def __unicode__(self):
        return '%s: %s' % (self.data.__class__.__name__,
                            super(ErrorString, self).__unicode__())


class ErrorOutput(object):
    """
    Wrapper class for file-like error streams with
    failsave de- and encoding of `str`, `bytes`, `unicode` and
    `Exception` instances.
    """

    def __init__(self, stream=None, encoding=None,
                 encoding_errors='backslashreplace',
                 decoding_errors='replace'):
        """
        :Parameters:
            - `stream`: a file-like object,
                        a string (path to a file),
                        `None` (write to `sys.stderr`, default), or
                        evaluating to `False` (write() requests are ignored).
            - `encoding`: `stream` text encoding. Guessed if None.
            - `encoding_errors`: how to treat encoding errors.
        """
        if stream is None:
            stream = sys.stderr
        elif not(stream):
            stream = False
        # if `stream` is a file name, open it
        elif isinstance(stream, str):
            stream = open(stream, 'w')
        elif isinstance(stream, str):
            stream = open(stream.encode(sys.getfilesystemencoding()), 'w')

        self.stream = stream
        """Where warning output is sent."""

        self.encoding = (encoding or getattr(stream, 'encoding', None) or
                         locale_encoding or 'ascii')
        """The output character encoding."""

        self.encoding_errors = encoding_errors
        """Encoding error handler."""

        self.decoding_errors = decoding_errors
        """Decoding error handler."""

    def write(self, data):
        """
        Write `data` to self.stream. Ignore, if self.stream is False.

        `data` can be a `string`, `unicode`, or `Exception` instance.
        """
        if self.stream is False:
            return
        if isinstance(data, Exception):
            data = str(SafeString(data, self.encoding,
                                  self.encoding_errors, self.decoding_errors))
        try:
            self.stream.write(data)
        except UnicodeEncodeError:
            self.stream.write(data.encode(self.encoding, self.encoding_errors))
        except TypeError: 
            if isinstance(data, str): # passed stream may expect bytes
                self.stream.write(data.encode(self.encoding, 
                                              self.encoding_errors))
                return
            if self.stream in (sys.stderr, sys.stdout):
                self.stream.buffer.write(data) # write bytes to raw stream
            else:
                self.stream.write(str(data, self.encoding,
                                          self.decoding_errors))

    def close(self):
        """
        Close the error-output stream.

        Ignored if the stream is` sys.stderr` or `sys.stdout` or has no
        close() method.
        """
        if self.stream in (sys.stdout, sys.stderr):
            return
        try:
            self.stream.close()
        except AttributeError:
            pass

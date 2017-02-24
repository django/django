"""Email backend that writes messages to a file."""

import datetime
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.console import \
    EmailBackend as ConsoleEmailBackend


class EmailBackend(ConsoleEmailBackend):
    def __init__(self, *args, file_path=None, **kwargs):
        self._fname = None
        if file_path is not None:
            self.file_path = file_path
        else:
            self.file_path = getattr(settings, 'EMAIL_FILE_PATH', None)
        # Make sure self.file_path is a string.
        if not isinstance(self.file_path, str):
            raise ImproperlyConfigured('Path for saving emails is invalid: %r' % self.file_path)
        self.file_path = os.path.abspath(self.file_path)
        # Make sure that self.file_path is an directory if it exists.
        if os.path.exists(self.file_path) and not os.path.isdir(self.file_path):
            raise ImproperlyConfigured(
                'Path for saving email messages exists, but is not a directory: %s' % self.file_path
            )
        # Try to create it, if it not exists.
        elif not os.path.exists(self.file_path):
            try:
                os.makedirs(self.file_path)
            except OSError as err:
                raise ImproperlyConfigured(
                    'Could not create directory for saving email messages: %s (%s)' % (self.file_path, err)
                )
        # Make sure that self.file_path is writable.
        if not os.access(self.file_path, os.W_OK):
            raise ImproperlyConfigured('Could not write to directory: %s' % self.file_path)
        # Finally, call super().
        # Since we're using the console-based backend as a base,
        # force the stream to be None, so we don't default to stdout
        kwargs['stream'] = None
        super().__init__(*args, **kwargs)

    def write_message(self, message):
        self.stream.write(message.message().as_bytes() + b'\n')
        self.stream.write(b'-' * 79)
        self.stream.write(b'\n')

    def _get_filename(self):
        """Return a unique file name."""
        if self._fname is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = "%s-%s.log" % (timestamp, abs(id(self)))
            self._fname = os.path.join(self.file_path, fname)
        return self._fname

    def open(self):
        if self.stream is None:
            self.stream = open(self._get_filename(), 'ab')
            return True
        return False

    def close(self):
        try:
            if self.stream is not None:
                self.stream.close()
        finally:
            self.stream = None

"""Email backend that writes messages to a file."""

import datetime
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


class EmailBackend(ConsoleEmailBackend):
    def __init__(self, *args, file_path=None, provider=None, **kwargs):
        self._fname = None

        if provider is not None:
            # Being initialized from EMAIL_PROVIDERS.
            options = settings.EMAIL_PROVIDERS[provider].get("OPTIONS", {})
            file_path = options.get("file_path")
        else:
            # RemovedInDjango70Warning: Not being initialized from
            # EMAIL_PROVIDERS. Check the deprecated EMAIL_FILE_PATH settings.
            file_path = file_path or getattr(settings, "EMAIL_FILE_PATH", None)

        if not file_path:
            raise ImproperlyConfigured(
                f'"file_path" not specified'
                f' in EMAIL_PROVIDERS["{provider}"]["OPTIONS"].'
            )
        self.file_path = os.path.abspath(file_path)
        try:
            os.makedirs(self.file_path, exist_ok=True)
        except FileExistsError:
            raise ImproperlyConfigured(
                "Path for saving email messages exists, but is not a directory: %s"
                % self.file_path
            )
        except OSError as err:
            raise ImproperlyConfigured(
                "Could not create directory for saving email messages: %s (%s)"
                % (self.file_path, err)
            )
        # Make sure that self.file_path is writable.
        if not os.access(self.file_path, os.W_OK):
            raise ImproperlyConfigured(
                "Could not write to directory: %s" % self.file_path
            )
        # Finally, call super().
        # Since we're using the console-based backend as a base,
        # force the stream to be None, so we don't default to stdout
        kwargs["stream"] = None
        super().__init__(*args, **kwargs)

    def write_message(self, message):
        self.stream.write(message.message().as_bytes() + b"\n")
        self.stream.write(b"-" * 79)
        self.stream.write(b"\n")

    def _get_filename(self):
        """Return a unique file name."""
        if self._fname is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = "%s-%s.log" % (timestamp, abs(id(self)))
            self._fname = os.path.join(self.file_path, fname)
        return self._fname

    def open(self):
        if self.stream is None:
            self.stream = open(self._get_filename(), "ab")
            return True
        return False

    def close(self):
        try:
            if self.stream is not None:
                self.stream.close()
        finally:
            self.stream = None

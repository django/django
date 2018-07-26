"""
Email backend that writes messages to console instead of sending them.
"""
import sys
import threading

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
from django.utils.translation import gettext as _


class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        self.stream = kwargs.pop('stream', sys.stdout)
        self._lock = threading.RLock()
        super().__init__(*args, **kwargs)

    def _output_if_exists(self, prefix, addresses, encoding):
        if not addresses:
            return

        line = ', '.join([sanitize_address(addr, encoding) for addr in addresses])
        self.stream.write('%s %s\n' % (prefix, line))

    def write_message(self, message):
        encoding = message.encoding or settings.DEFAULT_CHARSET
        self.stream.write(_('Recipients') + '\n')
        self._output_if_exists('To:', message.to, encoding)
        self._output_if_exists('Cc:', message.cc, encoding)
        self._output_if_exists('Bcc:', message.bcc, encoding)

        self.stream.write(_('MIME Text') + '\n')
        msg = message.message()
        charset = msg.get_charset().get_output_charset() if msg.get_charset() else 'utf-8'
        data = msg.as_bytes().decode(charset)
        self.stream.write('%s\n' % data)
        self.stream.write('-' * 79)
        self.stream.write('\n')

    def send_messages(self, email_messages):
        """Write all messages to the stream in a thread-safe way."""
        if not email_messages:
            return
        msg_count = 0
        with self._lock:
            try:
                stream_created = self.open()
                for message in email_messages:
                    self.write_message(message)
                    self.stream.flush()  # flush after each message
                    msg_count += 1
                if stream_created:
                    self.close()
            except Exception:
                if not self.fail_silently:
                    raise
        return msg_count

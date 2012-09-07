"""
Email backend that writes messages to console instead of sending them.
"""
import sys
import threading

from django.core.mail.backends.base import BaseEmailBackend

class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        self.stream = kwargs.pop('stream', sys.stdout)
        self._lock = threading.RLock()
        super(EmailBackend, self).__init__(*args, **kwargs)

    def send_messages(self, email_messages):
        """Write all messages to the stream in a thread-safe way."""
        if not email_messages:
            return
        with self._lock:
            try:
                stream_created = self.open()
                for message in email_messages:
                    self.stream.write('%s\n' % message.message().as_string())
                    self.stream.write('-' * 79)
                    self.stream.write('\n')
                    self.stream.flush()  # flush after each message
                if stream_created:
                    self.close()
            except:
                if not self.fail_silently:
                    raise
        return len(email_messages)

"""
Email backend that writes messages to console instead of sending them.
"""

import sys
import threading
import warnings

from django.core.mail.backends.base import BaseEmailBackend
from django.utils.deprecation import RemovedInDjango71Warning


class EmailBackend(BaseEmailBackend):
    def __init__(
        self,
        fail_silently=False,
        *,
        raw=None,
        max_text_length=1024,
        **kwargs,
    ):
        self.stream = kwargs.pop("stream", sys.stdout)
        self._lock = threading.RLock()
        super().__init__(**kwargs)
        self.fail_silently = fail_silently

        # RemovedInDjango71Warning.
        # (Also change the parameter default to `raw=False`.)
        if raw is None:
            warnings.warn(
                RemovedInDjango71Warning(
                    "The console EmailBackend will default to raw=False in Django 7.1. "
                    "Add 'raw': True in MAILERS OPTIONS to preserve the old behavior."
                ),
            )
            raw = True
        self.raw = raw
        self.max_text_length = max_text_length

    def write_message(self, message):
        msg_data = self.serialize(message)
        self.stream.write("%s\n" % msg_data)
        self.stream.write("-" * 79)
        self.stream.write("\n")

    def serialize(self, message):
        if self.raw:
            return self.serialize_raw(message)
        return self.serialize_friendly(message)

    def serialize_raw(self, message):
        msg = message.message()
        msg_data = msg.as_bytes()
        charset = (
            msg.get_charset().get_output_charset() if msg.get_charset() else "utf-8"
        )
        return msg_data.decode(charset)

    def serialize_friendly(self, message):
        msg = message.message()
        formatted = "".join(self._serialize_part_friendly(msg))
        if message.bcc:
            # Use invalid header name "(Bcc):" to avoid accidents.
            bcc = ", ".join(str(address) for address in message.bcc)
            formatted = f"(Bcc): {bcc}\n{formatted}"
        return formatted

    def _serialize_part_friendly(self, part, level=0):
        # Headers.
        if part.is_multipart() and not part.get_boundary():
            part.set_boundary(f"=====multipart-boundary-{level}=====")
        for field, value in part.items():
            yield f"{field}: {value}\n"
        yield "\n"

        # Body.
        if part.is_multipart():
            boundary = part.get_boundary()
            for subpart in part.iter_parts():
                yield f"--{boundary}\n"
                yield from self._serialize_part_friendly(subpart, level + 1)
            yield f"--{boundary}--\n"
        else:
            content = part.get_content()
            if content:
                length = len(content)
                if isinstance(content, str):
                    if (
                        self.max_text_length is not None
                        and length > self.max_text_length
                    ):
                        truncated = length - self.max_text_length
                        yield content[: self.max_text_length]
                        yield f"\n[... {truncated:_} more characters]\n"
                    else:
                        yield content
                        if not content.endswith("\n"):
                            yield "\n"
                else:
                    content_type = part.get_content_type()
                    yield f"[Binary {content_type}: {length:_} bytes]\n"

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

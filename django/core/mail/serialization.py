"""
Convert EmailMessage instances to and from JSON-serializable data, so they can
be passed as arguments to a django.tasks Task.
"""

import base64
import email.message
import email.policy
from datetime import datetime
from email.parser import BytesParser

from django.utils.encoding import force_str
from django.utils.module_loading import import_string, qualname

from .message import EmailAlternative, EmailAttachment, EmailMessage

# Increment when the format changes, so a worker running a newer Django can
# still read messages queued by an older one.
SERIALIZATION_VERSION = 1

RECIPIENT_FIELDS = ("to", "cc", "bcc", "reply_to")

PLAIN_FIELDS = (
    *RECIPIENT_FIELDS,
    "subject",
    "body",
    "from_email",
    "extra_headers",
    "content_subtype",
    "encoding",
)


def serialize_message(message):
    """
    Return a JSON-serializable dict representing the EmailMessage message.
    """
    if not isinstance(message, EmailMessage):
        class_name = type(message).__qualname__
        raise TypeError(f"message must be an EmailMessage, not {class_name!r}.")
    data = {
        "version": SERIALIZATION_VERSION,
        "class": qualname(type(message)),
        "subject": force_str(message.subject),
        "body": force_str(message.body),
        "from_email": force_str(message.from_email),
        "extra_headers": {
            force_str(name): _serialize_header(value)
            for name, value in message.extra_headers.items()
        },
        "content_subtype": message.content_subtype,
        "encoding": message.encoding,
        "attachments": [
            _serialize_attachment(attachment) for attachment in message.attachments
        ],
    }
    for field in RECIPIENT_FIELDS:
        data[field] = [force_str(address) for address in getattr(message, field)]
    if hasattr(message, "alternatives"):
        data["alternatives"] = [
            [_serialize_content(content), mimetype]
            for content, mimetype in message.alternatives
        ]
    return data


def deserialize_message(data):
    """Return an EmailMessage from serialize_message() output."""
    version = data.get("version")
    if version != SERIALIZATION_VERSION:
        raise ValueError(f"Unsupported email serialization version {version!r}.")
    class_path = data["class"]
    cls = import_string(class_path)

    if not (isinstance(cls, type) and issubclass(cls, EmailMessage)):
        raise ValueError(f"{class_path!r} is not an EmailMessage subclass.")

    message = cls.__new__(cls)
    message._connection = None
    for field in PLAIN_FIELDS:
        setattr(message, field, data[field])
    message.attachments = [
        _deserialize_attachment(attachment) for attachment in data["attachments"]
    ]
    if "alternatives" in data:
        message.alternatives = [
            EmailAlternative(_deserialize_content(content), mimetype)
            for content, mimetype in data["alternatives"]
        ]
    return message


def _serialize_header(value):
    if isinstance(value, datetime):
        return str(email.policy.default.header_factory("Date", value))
    return force_str(value)


def _serialize_attachment(attachment):
    if isinstance(attachment, email.message.Message):
        return _serialize_content(attachment)
    filename, content, mimetype = attachment
    if isinstance(filename, tuple):
        filename = list(filename)
    return {
        "filename": filename,
        "content": _serialize_content(content),
        "mimetype": mimetype,
    }


def _deserialize_attachment(data):
    if "mime" in data:
        return _deserialize_content(data)
    filename = data["filename"]
    if isinstance(filename, list):
        filename = tuple(filename)
    return EmailAttachment(
        filename, _deserialize_content(data["content"]), data["mimetype"]
    )


def _serialize_content(content):
    """
    Return content tagged with its type, so that _deserialize_content() can
    restore it exactly.
    """
    if isinstance(content, EmailMessage):
        return {"email": serialize_message(content)}
    if isinstance(content, email.message.Message):
        return {"mime": _b64encode(content.as_bytes(policy=email.policy.default))}
    if isinstance(content, (bytes, bytearray, memoryview)):
        return {"bytes": _b64encode(content)}
    return {"text": force_str(content)}


def _deserialize_content(data):
    if "email" in data:
        return deserialize_message(data["email"])
    if "mime" in data:
        parser = BytesParser(_class=email.message.MIMEPart, policy=email.policy.default)
        return parser.parsebytes(base64.b64decode(data["mime"]))
    if "bytes" in data:
        return base64.b64decode(data["bytes"])
    return data["text"]


def _b64encode(value):
    return base64.b64encode(value).decode()

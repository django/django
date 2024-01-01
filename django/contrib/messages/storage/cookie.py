import binascii
import json

from django.conf import settings
from django.contrib.messages.storage.base import BaseStorage, Message
from django.core import signing
from django.http import SimpleCookie
from django.utils.safestring import SafeData, mark_safe


class MessageEncoder(json.JSONEncoder):
    """
    Compactly serialize instances of the ``Message`` class as JSON.
    """

    message_key = "__json_message"

    def default(self, obj):
        if isinstance(obj, Message):
            # Using 0/1 here instead of False/True to produce more compact json
            is_safedata = 1 if isinstance(obj.message, SafeData) else 0
            message = [self.message_key, is_safedata, obj.level, obj.message]
            if obj.extra_tags is not None:
                message.append(obj.extra_tags)
            return message
        return super().default(obj)


class MessageDecoder(json.JSONDecoder):
    """
    Decode JSON that includes serialized ``Message`` instances.
    """

    def process_messages(self, obj):
        if isinstance(obj, list) and obj:
            if obj[0] == MessageEncoder.message_key:
                if obj[1]:
                    obj[3] = mark_safe(obj[3])
                return Message(*obj[2:])
            return [self.process_messages(item) for item in obj]
        if isinstance(obj, dict):
            return {key: self.process_messages(value) for key, value in obj.items()}
        return obj

    def decode(self, s, **kwargs):
        decoded = super().decode(s, **kwargs)
        return self.process_messages(decoded)


class MessagePartSerializer:
    def dumps(self, obj):
        return [
            json.dumps(
                o,
                separators=(",", ":"),
                cls=MessageEncoder,
            )
            for o in obj
        ]


class MessagePartGatherSerializer:
    def dumps(self, obj):
        """
        The parameter is an already serialized list of Message objects. No need
        to serialize it again, only join the list together and encode it.
        """
        return ("[" + ",".join(obj) + "]").encode("latin-1")


class MessageSerializer:
    def loads(self, data):
        return json.loads(data.decode("latin-1"), cls=MessageDecoder)


class CookieStorage(BaseStorage):
    """
    Store messages in a cookie.
    """

    cookie_name = "messages"
    # uwsgi's default configuration enforces a maximum size of 4kb for all the
    # HTTP headers. In order to leave some room for other cookies and headers,
    # restrict the session cookie to 1/2 of 4kb. See #18781.
    max_cookie_size = 2048
    not_finished = "__messagesnotfinished__"
    not_finished_json = json.dumps("__messagesnotfinished__")
    key_salt = "django.contrib.messages"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signer = signing.get_cookie_signer(salt=self.key_salt)

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of messages from the messages cookie. If the
        not_finished sentinel value is found at the end of the message list,
        remove it and return a result indicating that not all messages were
        retrieved by this storage.
        """
        data = self.request.COOKIES.get(self.cookie_name)
        messages = self._decode(data)
        all_retrieved = not (messages and messages[-1] == self.not_finished)
        if messages and not all_retrieved:
            # remove the sentinel value
            messages.pop()
        return messages, all_retrieved

    def _update_cookie(self, encoded_data, response):
        """
        Either set the cookie with the encoded data if there is any data to
        store, or delete the cookie.
        """
        if encoded_data:
            response.set_cookie(
                self.cookie_name,
                encoded_data,
                domain=settings.SESSION_COOKIE_DOMAIN,
                secure=settings.SESSION_COOKIE_SECURE or None,
                httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        else:
            response.delete_cookie(
                self.cookie_name,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )

    def _store(self, messages, response, remove_oldest=True, *args, **kwargs):
        """
        Store the messages to a cookie and return a list of any messages which
        could not be stored.

        If the encoded data is larger than ``max_cookie_size``, remove
        messages until the data fits (these are the messages which are
        returned), and add the not_finished sentinel value to indicate as much.
        """
        unstored_messages = []
        serialized_messages = MessagePartSerializer().dumps(messages)
        encoded_data = self._encode_parts(serialized_messages)
        if self.max_cookie_size:
            # data is going to be stored eventually by SimpleCookie, which
            # adds its own overhead, which we must account for.
            cookie = SimpleCookie()  # create outside the loop

            def is_too_large_for_cookie(data):
                return data and len(cookie.value_encode(data)[1]) > self.max_cookie_size

            def compute_msg(some_serialized_msg):
                return self._encode_parts(
                    some_serialized_msg + [self.not_finished_json],
                    encode_empty=True,
                )

            if is_too_large_for_cookie(encoded_data):
                if remove_oldest:
                    idx = bisect_keep_right(
                        serialized_messages,
                        fn=lambda m: is_too_large_for_cookie(compute_msg(m)),
                    )
                    unstored_messages = messages[:idx]
                    encoded_data = compute_msg(serialized_messages[idx:])
                else:
                    idx = bisect_keep_left(
                        serialized_messages,
                        fn=lambda m: is_too_large_for_cookie(compute_msg(m)),
                    )
                    unstored_messages = messages[idx:]
                    encoded_data = compute_msg(serialized_messages[:idx])

        self._update_cookie(encoded_data, response)
        return unstored_messages

    def _encode_parts(self, messages, encode_empty=False):
        """
        Return an encoded version of the serialized messages list which can be
        stored as plain text.

        Since the data will be retrieved from the client-side, the encoded data
        also contains a hash to ensure that the data was not tampered with.
        """
        if messages or encode_empty:
            return self.signer.sign_object(
                messages, serializer=MessagePartGatherSerializer, compress=True
            )

    def _encode(self, messages, encode_empty=False):
        """
        Return an encoded version of the messages list which can be stored as
        plain text.

        Proxies MessagePartSerializer.dumps and _encoded_parts.
        """
        serialized_messages = MessagePartSerializer().dumps(messages)
        return self._encode_parts(serialized_messages, encode_empty=encode_empty)

    def _decode(self, data):
        """
        Safely decode an encoded text stream back into a list of messages.

        If the encoded text stream contained an invalid hash or was in an
        invalid format, return None.
        """
        if not data:
            return None
        try:
            return self.signer.unsign_object(data, serializer=MessageSerializer)
        except (signing.BadSignature, binascii.Error, json.JSONDecodeError):
            pass
        # Mark the data as used (so it gets removed) since something was wrong
        # with the data.
        self.used = True
        return None


def bisect_keep_left(a, fn):
    """
    Find the index of the first element from the start of the array that
    verifies the given condition.
    The function is applied from the start of the array to the pivot.
    """
    lo = 0
    hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if fn(a[: mid + 1]):
            hi = mid
        else:
            lo = mid + 1
    return lo


def bisect_keep_right(a, fn):
    """
    Find the index of the first element from the end of the array that verifies
    the given condition.
    The function is applied from the pivot to the end of array.
    """
    lo = 0
    hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if fn(a[mid:]):
            lo = mid + 1
        else:
            hi = mid
    return lo

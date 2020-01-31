import json

from django.conf import settings
from django.contrib.messages.storage.base import BaseStorage, Message
from django.http import SimpleCookie
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.safestring import SafeData, mark_safe


class MessageEncoder(json.JSONEncoder):
    """
    Compactly serialize instances of the ``Message`` class as JSON.
    """
    message_key = '__json_message'

    def default(self, obj):
        if isinstance(obj, Message):
            # Using 0/1 here instead of False/True to produce more compact json
            is_safedata = 1 if isinstance(obj.message, SafeData) else 0
            message = [self.message_key, is_safedata, obj.level, obj.message]
            if obj.extra_tags:
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
            return {key: self.process_messages(value)
                    for key, value in obj.items()}
        return obj

    def decode(self, s, **kwargs):
        decoded = super().decode(s, **kwargs)
        return self.process_messages(decoded)


class CookieStorage(BaseStorage):
    """
    Store messages in a cookie.
    """
    cookie_name = 'messages'
    # uwsgi's default configuration enforces a maximum size of 4kb for all the
    # HTTP headers. In order to leave some room for other cookies and headers,
    # restrict the session cookie to 1/2 of 4kb. See #18781.
    max_cookie_size = 2048
    not_finished = '__messagesnotfinished__'

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
                self.cookie_name, encoded_data,
                domain=settings.SESSION_COOKIE_DOMAIN,
                secure=settings.SESSION_COOKIE_SECURE or None,
                httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        else:
            response.delete_cookie(self.cookie_name, domain=settings.SESSION_COOKIE_DOMAIN)

    def _store(self, messages, response, remove_oldest=True, *args, **kwargs):
        """
        Store the messages to a cookie and return a list of any messages which
        could not be stored.

        If the encoded data is larger than ``max_cookie_size``, remove
        messages until the data fits (these are the messages which are
        returned), and add the not_finished sentinel value to indicate as much.
        """
        unstored_messages = []
        encoded_data = self._encode(messages)
        if self.max_cookie_size:
            # data is going to be stored eventually by SimpleCookie, which
            # adds its own overhead, which we must account for.
            cookie = SimpleCookie()  # create outside the loop

            def stored_length(val):
                return len(cookie.value_encode(val)[1])

            while encoded_data and stored_length(encoded_data) > self.max_cookie_size:
                if remove_oldest:
                    unstored_messages.append(messages.pop(0))
                else:
                    unstored_messages.insert(0, messages.pop())
                encoded_data = self._encode(messages + [self.not_finished],
                                            encode_empty=unstored_messages)
        self._update_cookie(encoded_data, response)
        return unstored_messages

    def _hash(self, value):
        """
        Create an HMAC/SHA1 hash based on the value and the project setting's
        SECRET_KEY, modified to make it unique for the present purpose.
        """
        key_salt = 'django.contrib.messages'
        return salted_hmac(key_salt, value).hexdigest()

    def _encode(self, messages, encode_empty=False):
        """
        Return an encoded version of the messages list which can be stored as
        plain text.

        Since the data will be retrieved from the client-side, the encoded data
        also contains a hash to ensure that the data was not tampered with.
        """
        if messages or encode_empty:
            encoder = MessageEncoder(separators=(',', ':'))
            value = encoder.encode(messages)
            return '%s$%s' % (self._hash(value), value)

    def _decode(self, data):
        """
        Safely decode an encoded text stream back into a list of messages.

        If the encoded text stream contained an invalid hash or was in an
        invalid format, return None.
        """
        if not data:
            return None
        bits = data.split('$', 1)
        if len(bits) == 2:
            hash, value = bits
            if constant_time_compare(hash, self._hash(value)):
                try:
                    # If we get here (and the JSON decode works), everything is
                    # good. In any other case, drop back and return None.
                    return json.loads(value, cls=MessageDecoder)
                except json.JSONDecodeError:
                    pass
        # Mark the data as used (so it gets removed) since something was wrong
        # with the data.
        self.used = True
        return None

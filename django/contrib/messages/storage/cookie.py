import hmac

from django.conf import settings
from django.utils.hashcompat import sha_hmac
from django.contrib.messages import constants
from django.contrib.messages.storage.base import BaseStorage, Message
from django.utils import simplejson as json


class MessageEncoder(json.JSONEncoder):
    """
    Compactly serializes instances of the ``Message`` class as JSON.
    """
    message_key = '__json_message'

    def default(self, obj):
        if isinstance(obj, Message):
            message = [self.message_key, obj.level, obj.message]
            if obj.extra_tags:
                message.append(obj.extra_tags)
            return message
        return super(MessageEncoder, self).default(obj)


class MessageDecoder(json.JSONDecoder):
    """
    Decodes JSON that includes serialized ``Message`` instances.
    """

    def process_messages(self, obj):
        if isinstance(obj, list) and obj:
            if obj[0] == MessageEncoder.message_key:
                return Message(*obj[1:])
            return [self.process_messages(item) for item in obj]
        if isinstance(obj, dict):
            return dict([(key, self.process_messages(value))
                         for key, value in obj.iteritems()])
        return obj

    def decode(self, s, **kwargs):
        decoded = super(MessageDecoder, self).decode(s, **kwargs)
        return self.process_messages(decoded)

class CookieStorage(BaseStorage):
    """
    Stores messages in a cookie.
    """
    cookie_name = 'messages'
    max_cookie_size = 4096
    not_finished = '__messagesnotfinished__'

    def _get(self, *args, **kwargs):
        """
        Retrieves a list of messages from the messages cookie.  If the
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
        Either sets the cookie with the encoded data if there is any data to
        store, or deletes the cookie.
        """
        if encoded_data:
            response.set_cookie(self.cookie_name, encoded_data)
        else:
            response.delete_cookie(self.cookie_name)

    def _store(self, messages, response, remove_oldest=True, *args, **kwargs):
        """
        Stores the messages to a cookie, returning a list of any messages which
        could not be stored.

        If the encoded data is larger than ``max_cookie_size``, removes
        messages until the data fits (these are the messages which are
        returned), and add the not_finished sentinel value to indicate as much.
        """
        unstored_messages = []
        encoded_data = self._encode(messages)
        if self.max_cookie_size:
            while encoded_data and len(encoded_data) > self.max_cookie_size:
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
        Creates an HMAC/SHA1 hash based on the value and the project setting's
        SECRET_KEY, modified to make it unique for the present purpose.
        """
        key = 'django.contrib.messages' + settings.SECRET_KEY
        return hmac.new(key, value, sha_hmac).hexdigest()

    def _encode(self, messages, encode_empty=False):
        """
        Returns an encoded version of the messages list which can be stored as
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
        Safely decodes a encoded text stream back into a list of messages.

        If the encoded text stream contained an invalid hash or was in an
        invalid format, ``None`` is returned.
        """
        if not data:
            return None
        bits = data.split('$', 1)
        if len(bits) == 2:
            hash, value = bits
            if hash == self._hash(value):
                try:
                    # If we get here (and the JSON decode works), everything is
                    # good. In any other case, drop back and return None.
                    return json.loads(value, cls=MessageDecoder)
                except ValueError:
                    pass
        # Mark the data as used (so it gets removed) since something was wrong
        # with the data.
        self.used = True
        return None

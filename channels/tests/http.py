
import copy

from django.apps import apps
from django.conf import settings


from ..asgi import channel_layers
from ..message import Message
from ..sessions import session_for_reply_channel
from .base import Client


class HttpClient(Client):
    """
    Channel http/ws client abstraction that provides easy methods for testing full live cycle of message in channels
    with determined reply channel, auth opportunity, cookies, headers and so on
    """

    def __init__(self, **kwargs):
        super(HttpClient, self).__init__(**kwargs)
        self._session = None
        self._headers = {}
        self._cookies = {}

    def set_cookie(self, key, value):
        """
        Set cookie
        """
        self._cookies[key] = value

    def set_header(self, key, value):
        """
        Set header
        """
        if key == 'cookie':
            raise ValueError('Use set_cookie method for cookie header')
        self._headers[key] = value

    def get_cookies(self):
        """Return cookies"""
        cookies = copy.copy(self._cookies)
        if apps.is_installed('django.contrib.sessions'):
            cookies[settings.SESSION_COOKIE_NAME] = self.session.session_key
        return cookies

    @property
    def headers(self):
        headers = copy.deepcopy(self._headers)
        headers.setdefault('cookie', _encoded_cookies(self.get_cookies()))
        return headers

    @property
    def session(self):
        """Session as Lazy property: check that django.contrib.sessions is installed"""
        if not apps.is_installed('django.contrib.sessions'):
            raise EnvironmentError('Add django.contrib.sessions to the INSTALLED_APPS to use session')
        if not self._session:
            self._session = session_for_reply_channel(self.reply_channel)
        return self._session

    @property
    def channel_layer(self):
        """Channel layer as lazy property"""
        return channel_layers[self.alias]

    def get_next_message(self, channel):
        """
        Gets the next message that was sent to the channel during the test,
        or None if no message is available.

        If require is true, will fail the test if no message is received.
        """
        recv_channel, content = channel_layers[self.alias].receive_many([channel])
        if recv_channel is None:
            return
        return Message(content, recv_channel, channel_layers[self.alias])

    def send(self, to, content={}):
        """
        Send a message to a channel.
        Adds reply_channel name and channel_session to the message.
        """
        content = copy.deepcopy(content)
        content.setdefault('reply_channel', self.reply_channel)
        content.setdefault('path', '/')
        content.setdefault('headers', self.headers)
        self.channel_layer.send(to, content)

    def consume(self, channel):
        """
        Get next message for channel name and run appointed consumer
        """
        message = self.get_next_message(channel)
        if message:
            consumer, kwargs = self.channel_layer.router.match(message)
            return consumer(message, **kwargs)

    def send_and_consume(self, channel, content={}):
        """
        Reproduce full live cycle of the message
        """
        self.send(channel, content)
        return self.consume(channel)

    def receive(self):
        """
        Get content of next message for reply channel if message exists
        """
        message = self.get_next_message(self.reply_channel)
        if message:
            return message.content

    def login(self, **credentials):
        """
        Returns True if login is possible; False if the provided credentials
        are incorrect, or the user is inactive, or if the sessions framework is
        not available.
        """
        from django.contrib.auth import authenticate
        user = authenticate(**credentials)
        if user and user.is_active and apps.is_installed('django.contrib.sessions'):
            self._login(user)
            return True
        else:
            return False

    def force_login(self, user, backend=None):
        if backend is None:
            backend = settings.AUTHENTICATION_BACKENDS[0]
        user.backend = backend
        self._login(user)

    def _login(self, user):
        from django.contrib.auth import login

        # Fake http request
        request = type('FakeRequest', (object, ), {'session': self.session, 'META': {}})
        login(request, user)

        # Save the session values.
        self.session.save()


def _encoded_cookies(cookies):
    """Encode dict of cookies to ascii string"""
    return ('&'.join('{0}={1}'.format(k, v) for k, v in cookies.items())).encode("ascii")

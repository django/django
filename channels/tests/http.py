import copy
import json

import six
from django.apps import apps
from django.conf import settings

from django.http.cookie import SimpleCookie

from ..sessions import session_for_reply_channel
from .base import Client

json_module = json  # alias for using at functions with json kwarg


class HttpClient(Client):
    """
    Channel http/ws client abstraction that provides easy methods for testing full life cycle of message in channels
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

    def receive(self, json=True):
        """
        Return text content of a message for client channel and decoding it if json kwarg is set
        """
        content = super(HttpClient, self).receive()
        if content and json:
            return json_module.loads(content['text'])
        return content['text'] if content else None

    def send(self, to, content={}, text=None, path='/'):
        """
        Send a message to a channel.
        Adds reply_channel name and channel_session to the message.
        """
        content = copy.deepcopy(content)
        content.setdefault('reply_channel', self.reply_channel)
        content.setdefault('path', path)
        content.setdefault('headers', self.headers)
        text = text or content.get('text', None)
        if text is not None:
            if not isinstance(text, six.string_types):
                content['text'] = json.dumps(text)
            else:
                content['text'] = text
        self.channel_layer.send(to, content)

    def send_and_consume(self, channel, content={}, text=None, path='/', fail_on_none=True):
        """
        Reproduce full life cycle of the message
        """
        self.send(channel, content, text, path)
        return self.consume(channel, fail_on_none=fail_on_none)

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

    cookie_encoder = SimpleCookie()

    for k, v in cookies.items():
        cookie_encoder[k] = v

    return cookie_encoder.output(header='', sep=';').encode("ascii")

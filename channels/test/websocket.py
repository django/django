import copy
import json

import six
from django.apps import apps
from django.conf import settings

from django.http.cookie import SimpleCookie

from ..sessions import session_for_reply_channel
from .base import Client

json_module = json  # alias for using at functions with json kwarg


class WSClient(Client):
    """
    Channel http/ws client abstraction that provides easy methods for testing full life cycle of message in channels
    with determined reply channel, auth opportunity, cookies, headers and so on
    """

    def __init__(self, **kwargs):
        self._ordered = kwargs.pop('ordered', False)
        super(WSClient, self).__init__(**kwargs)
        self._session = None
        self._headers = {}
        self._cookies = {}
        self._session_cookie = True
        self.order = 0

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
        if self._session_cookie and apps.is_installed('django.contrib.sessions'):
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
        content = super(WSClient, self).receive()
        if content and json and 'text' in content and isinstance(content['text'], six.string_types):
            return json_module.loads(content['text'])
        return content.get('text', content) if content else None

    def send(self, to, content={}, text=None, path='/'):
        """
        Send a message to a channel.
        Adds reply_channel name and channel_session to the message.
        """
        if to != 'websocket.connect' and '?' in path:
            path = path.split('?')[0]
        self.channel_layer.send(to, self._get_content(content, text, path))
        self._session_cookie = False

    def _get_content(self, content={}, text=None, path='/'):
        content = copy.deepcopy(content)
        content.setdefault('reply_channel', self.reply_channel)

        if '?' in path:
            path, query_string = path.split('?')
            content.setdefault('path', path)
            content.setdefault('query_string', query_string)
        else:
            content.setdefault('path', path)

        content.setdefault('headers', self.headers)

        if self._ordered:
            if 'order' in content:
                raise ValueError('Do not use "order" manually with "ordered=True"')
            content['order'] = self.order
            self.order += 1

        text = text or content.get('text', None)

        if text is not None:
            if not isinstance(text, six.string_types):
                content['text'] = json.dumps(text)
            else:
                content['text'] = text
        return content

    def send_and_consume(self, channel, content={}, text=None, path='/', fail_on_none=True, check_accept=True):
        """
        Reproduce full life cycle of the message
        """
        self.send(channel, content, text, path)
        return self.consume(channel, fail_on_none=fail_on_none, check_accept=check_accept)

    def consume(self, channel, fail_on_none=True, check_accept=True):
        result = super(WSClient, self).consume(channel, fail_on_none=fail_on_none)
        if channel == "websocket.connect" and check_accept:
            received = self.receive(json=False)
            if received != {"accept": True}:
                raise AssertionError("Connection rejected: %s != '{accept: True}'" % received)
        return result

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

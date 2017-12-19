from __future__ import unicode_literals

from django.http.cookie import parse_cookie

from channels import route
from channels.exceptions import ChannelSocketException, WebsocketCloseException
from channels.handler import AsgiRequest
from channels.test import ChannelTestCase, WSClient, apply_routes
from channels.sessions import enforce_ordering


class WSClientTests(ChannelTestCase):
    def test_cookies(self):
        client = WSClient()
        client.set_cookie('foo', 'not-bar')
        client.set_cookie('foo', 'bar')
        client.set_cookie('qux', 'qu;x')

        # Django's interpretation of the serialized cookie.
        cookie_dict = parse_cookie(client.headers['cookie'].decode('ascii'))

        self.assertEqual(client.get_cookies(),
                         cookie_dict)

        self.assertEqual({'foo': 'bar',
                          'qux': 'qu;x',
                          'sessionid': client.get_cookies()['sessionid']},
                         cookie_dict)

    def test_simple_content(self):
        client = WSClient()
        content = client._get_content(text={'key': 'value'}, path='/my/path')

        self.assertEqual(content['text'], '{"key": "value"}')
        self.assertEqual(content['path'], '/my/path')
        self.assertTrue('reply_channel' in content)
        self.assertTrue('headers' in content)

    def test_path_in_content(self):
        client = WSClient()
        content = client._get_content(content={'path': '/my_path'}, text={'path': 'hi'}, path='/my/path')

        self.assertEqual(content['text'], '{"path": "hi"}')
        self.assertEqual(content['path'], '/my_path')
        self.assertTrue('reply_channel' in content)
        self.assertTrue('headers' in content)

    def test_session_in_headers(self):
        client = WSClient()
        content = client._get_content()
        self.assertTrue('path' in content)
        self.assertEqual(content['path'], '/')

        self.assertTrue('headers' in content)
        self.assertIn(b'cookie', [x[0] for x in content['headers']])
        self.assertIn(b'sessionid', [x[1] for x in content['headers'] if x[0] == b'cookie'][0])

    def test_ordering_in_content(self):
        client = WSClient(ordered=True)
        content = client._get_content()
        self.assertTrue('order' in content)
        self.assertEqual(content['order'], 0)
        client.order = 2
        content = client._get_content()
        self.assertTrue('order' in content)
        self.assertEqual(content['order'], 2)

    def test_ordering(self):

        client = WSClient(ordered=True)

        @enforce_ordering
        def consumer(message):
            message.reply_channel.send({'text': message['text']})

        with apply_routes(route('websocket.receive', consumer)):
            client.send_and_consume('websocket.receive', text='1')  # order = 0
            client.send_and_consume('websocket.receive', text='2')  # order = 1
            client.send_and_consume('websocket.receive', text='3')  # order = 2

            self.assertEqual(client.receive(), 1)
            self.assertEqual(client.receive(), 2)
            self.assertEqual(client.receive(), 3)

    def test_get_params(self):
        client = WSClient()
        content = client._get_content(path='/my/path?test=1&token=2')
        self.assertTrue('path' in content)
        self.assertTrue('query_string' in content)
        self.assertEqual(content['path'], '/my/path')
        self.assertEqual(content['query_string'], 'test=1&token=2')

    def test_get_params_with_consumer(self):
        client = WSClient(ordered=True)

        def consumer(message):
            message.content['method'] = 'FAKE'
            message.reply_channel.send({'text': dict(AsgiRequest(message).GET)})

        with apply_routes([route('websocket.receive', consumer, path=r'^/test'),
                           route('websocket.connect', consumer, path=r'^/test')]):
            path = '/test?key1=val1&key2=val2&key1=val3'
            client.send_and_consume('websocket.connect', path=path, check_accept=False)
            self.assertDictEqual(client.receive(), {'key2': ['val2'], 'key1': ['val1', 'val3']})

            client.send_and_consume('websocket.receive', path=path)
            self.assertDictEqual(client.receive(), {})

    def test_channel_socket_exception(self):

        class MyChannelSocketException(ChannelSocketException):

            def run(self, message):
                message.reply_channel.send({'text': 'error'})

        def consumer(message):
            raise MyChannelSocketException

        client = WSClient()
        with apply_routes(route('websocket.receive', consumer)):
            client.send_and_consume('websocket.receive')

            self.assertEqual(client.receive(json=False), 'error')

    def test_websocket_close_exception(self):

        def consumer(message):
            raise WebsocketCloseException

        client = WSClient(reply_channel='daphne.response.1')

        with apply_routes(route('websocket.receive', consumer)):
            client.send_and_consume('websocket.receive')

        self.assertEqual(client.get_next_message(client.reply_channel).content, {'close': True})

    def test_websocket_close_exception_close_code(self):

        def consumer(message):
            raise WebsocketCloseException(3001)

        client = WSClient(reply_channel='daphne.response.1')

        with apply_routes(route('websocket.receive', consumer)):
            client.send_and_consume('websocket.receive')

        self.assertEqual(client.get_next_message(client.reply_channel).content, {'close': 3001})

    def test_websocket_close_exception_invalid_close_code(self):

        with self.assertRaises(ValueError):
            WebsocketCloseException(2000)

        with self.assertRaises(ValueError):
            WebsocketCloseException('code')

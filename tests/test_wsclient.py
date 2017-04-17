from __future__ import unicode_literals

from django.http.cookie import parse_cookie

from channels.test import ChannelTestCase, WSClient


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

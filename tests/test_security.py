from __future__ import unicode_literals

from django.test import override_settings
from channels.exceptions import DenyConnection
from channels.security.websockets import allowed_hosts_only
from channels.message import Message
from channels.test import ChannelTestCase


@allowed_hosts_only
def connect(message):
    return True


class OriginValidationTestCase(ChannelTestCase):

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_valid_origin(self):
        content = {
            'headers': [[b'origin', b'http://example.com']]
        }
        message = Message(content, 'websocket.connect', None)
        self.assertTrue(connect(message))

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_invalid_origin(self):
        content = {
            'headers': [[b'origin', b'http://example.org']]
        }
        message = Message(content, 'websocket.connect', None)
        self.assertRaises(DenyConnection, connect, message)

    def test_invalid_origin_header(self):
        invalid_headers = [
            [],  # origin header missing
            [b'origin', b''],  # origin header empty
            [b'origin', b'\xc3\xa4']  # non-ascii
        ]
        for headers in invalid_headers:
            content = {
                'headers': [headers]
            }
            message = Message(content, 'websocket.connect', None)
            self.assertRaises(DenyConnection, connect, message)

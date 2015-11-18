from django.test import TestCase

from channels.interfaces.websocket_autobahn import get_protocol

try:
    from unittest import mock
except ImportError:
    import mock


def generate_connection_request(path, params, headers):
    request = mock.Mock()
    request.path = path
    request.params = params
    request.headers = headers
    return request


class WebsocketAutobahnInterfaceProtocolTestCase(TestCase):
    def test_on_connect_cookie(self):
        protocol = get_protocol(object)()
        session = "123cat"
        cookie = "somethingelse=test; sessionid={0}".format(session)
        headers = {
            "cookie": cookie
        }

        test_request = generate_connection_request("path", {}, headers)
        protocol.onConnect(test_request)
        self.assertEqual(session, protocol.request_info["cookies"]["sessionid"])

    def test_on_connect_no_cookie(self):
        protocol = get_protocol(object)()
        test_request = generate_connection_request("path", {}, {})
        protocol.onConnect(test_request)
        self.assertEqual({}, protocol.request_info["cookies"])

    def test_on_connect_params(self):
        protocol = get_protocol(object)()
        params = {
            "session_key": ["123cat"]
        }

        test_request = generate_connection_request("path", params, {})
        protocol.onConnect(test_request)
        self.assertEqual(params, protocol.request_info["get"])

    def test_on_connect_path(self):
        protocol = get_protocol(object)()
        path = "path"
        test_request = generate_connection_request(path, {}, {})
        protocol.onConnect(test_request)
        self.assertEqual(path, protocol.request_info["path"])

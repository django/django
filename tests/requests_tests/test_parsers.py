from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from django.http.parsers import BaseParser, FormParser, JSONParser, MultiPartParser
from django.test import SimpleTestCase
from django.test.client import FakePayload
from django.utils.http import urlencode


class TestParsers(SimpleTestCase):
    def test_can_handle(self):
        parser = MultiPartParser(HttpRequest())
        self.assertIs(parser.can_handle("multipart/form-data"), True)
        self.assertIs(parser.can_handle("application/json"), False)

        parser = FormParser(HttpRequest())
        self.assertIs(parser.can_handle("application/x-www-form-urlencoded"), True)
        self.assertIs(parser.can_handle("multipart/form-data"), False)

    def test_custom_can_handle(self):
        class CustomParser(BaseParser):
            media_type = "text/*"

            def can_handle(self, media_type):
                main_type, sub_type = media_type.split("/")
                return main_type == "text"

        parser = CustomParser(None)
        self.assertIs(parser.can_handle("application/json"), False)
        self.assertTrue(parser.can_handle("text/*"), True)
        self.assertTrue(parser.can_handle("text/csv"), True)

    def test_request_parser_no_setting(self):
        request = HttpRequest()
        form, multipart, json = request.parsers
        self.assertIs(form, FormParser)
        self.assertIs(multipart, MultiPartParser)
        self.assertIs(json, JSONParser)

    def test_set_parser(self):
        request = HttpRequest()
        request.parsers = [FormParser]

        self.assertEqual(len(request.parsers), 1)
        self.assertIs(request.parsers[0], FormParser)

    def test_set_parsers_following_files_access(self):
        payload = FakePayload(urlencode({"key": "value"}))
        request = WSGIRequest(
            {
                "REQUEST_METHOD": "POST",
                "CONTENT_LENGTH": len(payload),
                "CONTENT_TYPE": "application/x-www-form-urlencoded",
                "wsgi.input": payload,
            }
        )
        # can set parsers
        request.parsers = []
        # access files
        request.FILES
        msg = "You cannot change parsers after processing the request's content."
        with self.assertRaisesMessage(AttributeError, msg):
            request.parsers = []

    def test_json_strict(self):
        parser = JSONParser(None)

        msg_base = "Out of range float values are not JSON compliant: '%s'"
        for value in ["Infinity", "-Infinity", "NaN"]:
            with self.subTest(value=value):
                msg = msg_base % value
                with self.assertRaisesMessage(ValueError, msg):
                    parser.parse(bytes(value.encode()))

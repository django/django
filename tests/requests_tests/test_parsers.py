from unittest import TestCase

from django.http.parsers import BaseParser, FormParser, MultiPartParser


class TestParsers(TestCase):
    def test_can_handle(self):
        parser = MultiPartParser()
        self.assertIs(parser.can_handle("multipart/form-data"), True)
        self.assertIs(parser.can_handle("application/json"), False)

        parser = FormParser()
        self.assertIs(parser.can_handle("application/x-www-form-urlencoded"), True)
        self.assertIs(parser.can_handle("multipart/form-data"), False)

    def test_custom_can_handle(self):
        class CustomParser(BaseParser):
            media_type = "text/*"

            def can_handle(self, media_type):
                main_type, sub_type = media_type.split("/")
                return main_type == "text"

        parser = CustomParser()
        self.assertIs(parser.can_handle("application/json"), False)
        self.assertTrue(parser.can_handle("text/*"), True)
        self.assertTrue(parser.can_handle("text/csv"), True)

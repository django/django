from unittest import TestCase

from django.http import HttpRequest
from django.http.request import MediaType


class MediaTypeTests(TestCase):
    def test_empty(self):
        for empty_media_type in (None, ""):
            with self.subTest(media_type=empty_media_type):
                media_type = MediaType(empty_media_type)
                self.assertIs(media_type.is_all_types, False)
                self.assertEqual(str(media_type), "")
                self.assertEqual(repr(media_type), "<MediaType: >")

    def test_str(self):
        self.assertEqual(str(MediaType("*/*; q=0.8")), "*/*; q=0.8")
        self.assertEqual(str(MediaType("application/xml")), "application/xml")

    def test_repr(self):
        self.assertEqual(repr(MediaType("*/*; q=0.8")), "<MediaType: */*; q=0.8>")
        self.assertEqual(
            repr(MediaType("application/xml")),
            "<MediaType: application/xml>",
        )

    def test_is_all_types(self):
        self.assertIs(MediaType("*/*").is_all_types, True)
        self.assertIs(MediaType("*/*; q=0.8").is_all_types, True)
        self.assertIs(MediaType("text/*").is_all_types, False)
        self.assertIs(MediaType("application/xml").is_all_types, False)

    def test_match(self):
        tests = [
            ("*/*; q=0.8", "*/*"),
            ("*/*", "application/json"),
            (" */* ", "application/json"),
            ("application/*", "application/json"),
            ("application/xml", "application/xml"),
            (" application/xml ", "application/xml"),
            ("application/xml", " application/xml "),
        ]
        for accepted_type, mime_type in tests:
            with self.subTest(accepted_type, mime_type=mime_type):
                self.assertIs(MediaType(accepted_type).match(mime_type), True)

    def test_no_match(self):
        tests = [
            (None, "*/*"),
            ("", "*/*"),
            ("; q=0.8", "*/*"),
            ("application/xml", "application/html"),
            ("application/xml", "*/*"),
        ]
        for accepted_type, mime_type in tests:
            with self.subTest(accepted_type, mime_type=mime_type):
                self.assertIs(MediaType(accepted_type).match(mime_type), False)

    def test_quality(self):
        tests = [
            ("*/*; q=0.8", 0.8),
            ("*/*; q=0.0001", 0),
            ("*/*; q=0.12345", 0.123),
            ("*/*; q=0.1", 0.1),
            ("*/*; q=-1", 1),
            ("*/*; q=2", 1),
            ("*/*; q=h", 1),
            ("*/*", 1),
        ]
        for accepted_type, quality in tests:
            with self.subTest(accepted_type, quality=quality):
                self.assertEqual(MediaType(accepted_type).quality, quality)

    def test_specificity(self):
        tests = [
            ("*/*", 0),
            ("*/*;q=0.5", 0),
            ("text/*", 1),
            ("text/*;q=0.5", 1),
            ("text/html", 2),
            ("text/html;q=1", 2),
            ("text/html;q=0.5", 3),
        ]
        for accepted_type, specificity in tests:
            with self.subTest(accepted_type, specificity=specificity):
                self.assertEqual(MediaType(accepted_type).specificity, specificity)


class AcceptHeaderTests(TestCase):
    def test_no_headers(self):
        """Absence of Accept header defaults to '*/*'."""
        request = HttpRequest()
        self.assertEqual(
            [str(accepted_type) for accepted_type in request.accepted_types],
            ["*/*"],
        )

    def test_accept_headers(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = (
            "text/*,text/html, application/xhtml+xml,application/xml ;q=0.9,*/*;q=0.8,"
        )
        self.assertEqual(
            [str(accepted_type) for accepted_type in request.accepted_types],
            [
                "text/html",
                "application/xhtml+xml",
                "text/*",
                "application/xml; q=0.9",
                "*/*; q=0.8",
            ],
        )

    def test_request_accepts_any(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "*/*"
        self.assertIs(request.accepts("application/json"), True)
        self.assertIsNone(request.get_preferred_type([]))
        self.assertEqual(
            request.get_preferred_type(["application/json", "text/plain"]),
            "application/json",
        )

    def test_request_accepts_none(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = ""
        self.assertIs(request.accepts("application/json"), False)
        self.assertEqual(request.accepted_types, [])
        self.assertIsNone(
            request.get_preferred_type(["application/json", "text/plain"])
        )

    def test_request_accepts_some(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9"
        )
        self.assertIs(request.accepts("text/html"), True)
        self.assertIs(request.accepts("application/xhtml+xml"), True)
        self.assertIs(request.accepts("application/xml"), True)
        self.assertIs(request.accepts("application/json"), False)

    def test_accept_header_priority(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = (
            "text/html,application/xml;q=0.9,*/*;q=0.1,text/*;q=0.5"
        )

        tests = [
            (["text/html", "application/xml"], "text/html"),
            (["application/xml", "application/json"], "application/xml"),
            (["application/json"], "application/json"),
            (["application/json", "text/plain"], "text/plain"),
        ]
        for types, preferred_type in tests:
            with self.subTest(types, preferred_type=preferred_type):
                self.assertEqual(str(request.get_preferred_type(types)), preferred_type)

    def test_accept_header_priority_overlapping_mime(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "text/*;q=0.8,text/html;q=0.8"

        self.assertEqual(
            [str(accepted_type) for accepted_type in request.accepted_types],
            [
                "text/html; q=0.8",
                "text/*; q=0.8",
            ],
        )

    def test_no_matching_accepted_type(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "text/html"

        self.assertIsNone(
            request.get_preferred_type(["application/json", "text/plain"])
        )

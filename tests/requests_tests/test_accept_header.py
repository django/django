from unittest import TestCase

from django.http import HttpRequest
from django.http.request import MediaType


class MediaTypeTests(TestCase):
    def test_empty(self):
        for empty_media_type in (None, "", "  "):
            with self.subTest(media_type=empty_media_type):
                media_type = MediaType(empty_media_type)
                self.assertEqual(str(media_type), "")
                self.assertEqual(repr(media_type), "<MediaType: >")

    def test_str(self):
        self.assertEqual(str(MediaType("*/*; q=0.8")), "*/*; q=0.8")
        self.assertEqual(str(MediaType("application/xml")), "application/xml")
        self.assertEqual(
            str(MediaType("application/xml;type=madeup;q=42")),
            "application/xml; type=madeup; q=42",
        )

    def test_repr(self):
        self.assertEqual(repr(MediaType("*/*; q=0.8")), "<MediaType: */*; q=0.8>")
        self.assertEqual(
            repr(MediaType("application/xml")),
            "<MediaType: application/xml>",
        )

    def test_match(self):
        tests = [
            ("*/*; q=0.8", "*/*"),
            ("*/*", "application/json"),
            (" */* ", "application/json"),
            ("application/*", "application/json"),
            ("application/*", "application/*"),
            ("application/xml", "application/xml"),
            (" application/xml ", "application/xml"),
            ("application/xml", " application/xml "),
            ("text/vcard; version=4.0", "text/vcard; version=4.0"),
            ("text/vcard; version=4.0; q=0.7", "text/vcard; version=4.0"),
            ("text/vcard; version=4.0", "text/vcard"),
        ]
        for accepted_type, mime_type in tests:
            with self.subTest(accepted_type, mime_type=mime_type):
                self.assertIs(MediaType(accepted_type).match(mime_type), True)

    def test_no_match(self):
        tests = [
            # other is falsey.
            ("*/*", None),
            ("*/*", ""),
            # other is malformed.
            ("*/*", "; q=0.8"),
            # main_type is falsey.
            ("/*", "*/*"),
            # other.main_type is falsey.
            ("*/*", "/*"),
            # main sub_type is falsey.
            ("application", "application/*"),
            # other.sub_type is falsey.
            ("application/*", "application"),
            # All main and sub types are defined, but there is no match.
            ("application/xml", "application/html"),
            ("text/vcard; version=4.0", "text/vcard; version=3.0"),
            ("text/vcard; q=0.7", "text/vcard; version=3.0"),
            ("text/vcard", "text/vcard; version=3.0"),
        ]
        for accepted_type, mime_type in tests:
            with self.subTest(accepted_type, mime_type=mime_type):
                self.assertIs(MediaType(accepted_type).match(mime_type), False)

    def test_params(self):
        tests = [
            ("text/plain", {}, {}),
            ("text/plain;q=0.7", {"q": "0.7"}, {}),
            ("text/plain;q=1.5", {"q": "1.5"}, {}),
            ("text/plain;q=xyz", {"q": "xyz"}, {}),
            ("text/plain;q=0.1234", {"q": "0.1234"}, {}),
            ("text/plain;version=2", {"version": "2"}, {"version": "2"}),
            (
                "text/plain;version=2;q=0.8",
                {"version": "2", "q": "0.8"},
                {"version": "2"},
            ),
            (
                "text/plain;q=0.8;version=2",
                {"q": "0.8", "version": "2"},
                {"version": "2"},
            ),
            (
                "text/plain; charset=UTF-8; q=0.3",
                {"charset": "UTF-8", "q": "0.3"},
                {"charset": "UTF-8"},
            ),
            (
                "text/plain ; q = 0.5 ; version = 3.0",
                {"q": "0.5", "version": "3.0"},
                {"version": "3.0"},
            ),
            ("text/plain; format=flowed", {"format": "flowed"}, {"format": "flowed"}),
            (
                "text/plain; format=flowed; q=0.4",
                {"format": "flowed", "q": "0.4"},
                {"format": "flowed"},
            ),
            ("text/*;q=0.2", {"q": "0.2"}, {}),
            ("*/json;q=0.9", {"q": "0.9"}, {}),
            ("application/json;q=0.9999", {"q": "0.9999"}, {}),
            ("text/html;q=0.0001", {"q": "0.0001"}, {}),
            ("text/html;q=0", {"q": "0"}, {}),
            ("text/html;q=0.", {"q": "0."}, {}),
            ("text/html;q=.8", {"q": ".8"}, {}),
            ("text/html;q= 0.9", {"q": "0.9"}, {}),
            ('text/html ; q = "0.6"', {"q": "0.6"}, {}),
        ]
        for accepted_type, params, range_params in tests:
            media_type = MediaType(accepted_type)
            with self.subTest(accepted_type, attr="params"):
                self.assertEqual(media_type.params, params)
            with self.subTest(accepted_type, attr="range_params"):
                self.assertEqual(media_type.range_params, range_params)

    def test_quality(self):
        tests = [
            ("*/*; q=0.8", 0.8),
            ("*/*; q=0.0001", 0),
            ("*/*; q=0.12345", 0.123),
            ("*/*; q=0.1", 0.1),
            ("*/*; q=-1", 1),
            ("*/*; q=2", 1),
            ("*/*; q=h", 1),
            ("*/*; q=inf", 1),
            ("*/*; q=0", 0),
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
            ("text/html;q=0.5", 2),
            ("text/html;version=5", 3),
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
        self.assertEqual(
            [
                str(accepted_type)
                for accepted_type in request.accepted_types_by_precedence
            ],
            [
                "text/html",
                "application/xhtml+xml",
                "application/xml; q=0.9",
                "text/*",
                "*/*; q=0.8",
            ],
        )

    def test_zero_quality(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "text/*;q=0,text/html"
        self.assertEqual(
            [str(accepted_type) for accepted_type in request.accepted_types],
            ["text/html"],
        )

    def test_precedence(self):
        """
        Taken from https://datatracker.ietf.org/doc/html/rfc7231#section-5.3.2.
        """
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = (
            "text/*, text/plain, text/plain;format=flowed, */*"
        )
        self.assertEqual(
            [
                str(accepted_type)
                for accepted_type in request.accepted_types_by_precedence
            ],
            [
                "text/plain; format=flowed",
                "text/plain",
                "text/*",
                "*/*",
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
        self.assertEqual(
            [
                str(accepted_type)
                for accepted_type in request.accepted_types_by_precedence
            ],
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

    def test_accept_with_param(self):
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "text/vcard; version=3.0, text/html;q=0.5"

        for media_types, expected in [
            (
                [
                    "text/vcard; version=4.0",
                    "text/vcard; version=3.0",
                    "text/vcard",
                    "text/directory",
                ],
                "text/vcard; version=3.0",
            ),
            (["text/vcard; version=4.0", "text/vcard", "text/directory"], None),
            (["text/vcard; version=4.0", "text/html"], "text/html"),
        ]:
            self.assertEqual(request.get_preferred_type(media_types), expected)

    def test_quality_for_media_type_rfc7231(self):
        """
        Taken from https://datatracker.ietf.org/doc/html/rfc7231#section-5.3.2.
        """
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = (
            "text/*;q=0.3,text/html;q=0.7,text/html;level=1,text/html;level=2;q=0.4,"
            "*/*;q=0.5"
        )

        for media_type, quality in [
            ("text/html;level=1", 1),
            ("text/html", 0.7),
            ("text/plain", 0.3),
            ("image/jpeg", 0.5),
            ("text/html;level=2", 0.4),
            ("text/html;level=3", 0.7),
        ]:
            with self.subTest(media_type):
                accepted_media_type = request.accepted_type(media_type)
                self.assertIsNotNone(accepted_media_type)
                self.assertEqual(accepted_media_type.quality, quality)

        for media_types, expected in [
            (["text/html", "text/html; level=1"], "text/html; level=1"),
            (["text/html; level=2", "text/html; level=3"], "text/html; level=3"),
        ]:
            self.assertEqual(request.get_preferred_type(media_types), expected)

    def test_quality_for_media_type_rfc9110(self):
        """
        Taken from
        https://www.rfc-editor.org/rfc/rfc9110.html#section-12.5.1-18.
        """
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = (
            "text/*;q=0.3, text/plain;q=0.7, text/plain;format=flowed, "
            "text/plain;format=fixed;q=0.4, */*;q=0.5"
        )

        for media_type, quality in [
            ("text/plain;format=flowed", 1),
            ("text/plain", 0.7),
            ("text/html", 0.3),
            ("image/jpeg", 0.5),
            ("text/plain;format=fixed", 0.4),
            ("text/html;level=3", 0.3),  # https://www.rfc-editor.org/errata/eid7138
        ]:
            with self.subTest(media_type):
                accepted_media_type = request.accepted_type(media_type)
                self.assertIsNotNone(accepted_media_type)
                self.assertEqual(accepted_media_type.quality, quality)

        for media_types, expected in [
            (["text/plain", "text/plain; format=flowed"], "text/plain; format=flowed"),
            (["text/html", "image/jpeg"], "image/jpeg"),
        ]:
            self.assertEqual(request.get_preferred_type(media_types), expected)

    def test_quality_breaks_specificity(self):
        """
        With the same specificity, the quality breaks the tie.
        """
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "text/plain;q=0.5,text/html"

        self.assertEqual(request.accepted_type("text/plain").quality, 0.5)
        self.assertEqual(request.accepted_type("text/plain").specificity, 2)

        self.assertEqual(request.accepted_type("text/html").quality, 1)
        self.assertEqual(request.accepted_type("text/html").specificity, 2)

        self.assertEqual(
            request.get_preferred_type(["text/html", "text/plain"]), "text/html"
        )

    def test_quality_over_specificity(self):
        """
        For media types with the same quality, prefer the more specific type.
        """
        request = HttpRequest()
        request.META["HTTP_ACCEPT"] = "text/*,image/jpeg"

        self.assertEqual(request.accepted_type("text/plain").quality, 1)
        self.assertEqual(request.accepted_type("text/plain").specificity, 1)

        self.assertEqual(request.accepted_type("image/jpeg").quality, 1)
        self.assertEqual(request.accepted_type("image/jpeg").specificity, 2)

        self.assertEqual(
            request.get_preferred_type(["text/plain", "image/jpeg"]), "image/jpeg"
        )

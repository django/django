from django.contrib.auth.hashers import make_password
from django.contrib.auth.templatetags.auth import render_password_as_hash
from django.test import SimpleTestCase, override_settings


class RenderPasswordAsHashTests(SimpleTestCase):
    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
    )
    def test_valid_password(self):
        value = (
            "pbkdf2_sha256$100000$a6Pucb1qSFcD$WmCkn9Hqidj48NVe5x0FEM6A9YiOqQcl/83m2Z5u"
            "dm0="
        )
        hashed_html = (
            "<p><strong>algorithm</strong>: <bdi>pbkdf2_sha256</bdi> "
            "<strong>iterations</strong>: <bdi>100000</bdi> "
            "<strong>salt</strong>: <bdi>a6Pucb******</bdi> "
            "<strong>hash</strong>: <bdi>WmCkn9**************************************"
            "</bdi></p>"
        )
        self.assertEqual(render_password_as_hash(value), hashed_html)

    def test_invalid_password(self):
        expected = (
            "<p><strong>Invalid password format or unknown hashing algorithm.</strong>"
            "</p>"
        )
        for value in ["pbkdf2_sh", "md5$password", "invalid", "testhash$password"]:
            with self.subTest(value=value):
                self.assertEqual(render_password_as_hash(value), expected)

    def test_no_password(self):
        expected = "<p><strong>No password set.</strong></p>"
        for value in ["", None, make_password(None)]:
            with self.subTest(value=value):
                self.assertEqual(render_password_as_hash(value), expected)

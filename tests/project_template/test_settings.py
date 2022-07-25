import shutil
import tempfile
from pathlib import Path

from django import conf
from django.test import SimpleTestCase
from django.test.utils import extend_sys_path


class TestStartProjectSettings(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        template_settings_py = (
            Path(conf.__file__).parent
            / "project_template"
            / "project_name"
            / "settings.py-tpl"
        )
        test_settings_py = Path(self.temp_dir.name) / "test_settings.py"
        shutil.copyfile(template_settings_py, test_settings_py)

    def test_middleware_headers(self):
        """
        Ensure headers sent by the default MIDDLEWARE don't inadvertently
        change. For example, we never want "Vary: Cookie" to appear in the list
        since it prevents the caching of responses.
        """
        with extend_sys_path(self.temp_dir.name):
            from test_settings import MIDDLEWARE

        with self.settings(
            MIDDLEWARE=MIDDLEWARE,
            ROOT_URLCONF="project_template.urls",
        ):
            response = self.client.get("/empty/")
            headers = sorted(response.serialize_headers().split(b"\r\n"))
            self.assertEqual(
                headers,
                [
                    b"Content-Length: 0",
                    b"Content-Type: text/html; charset=utf-8",
                    b"Cross-Origin-Opener-Policy: same-origin",
                    b"Referrer-Policy: same-origin",
                    b"X-Content-Type-Options: nosniff",
                    b"X-Frame-Options: DENY",
                ],
            )

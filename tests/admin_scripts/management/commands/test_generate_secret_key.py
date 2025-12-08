from django.core.management import call_command
from django.test import SimpleTestCase
from io import StringIO
import re

class GenerateSecretKeyTests(SimpleTestCase):
    def test_generates_valid_key(self):
        out = StringIO()
        call_command('generate_secret_key', stdout=out)
        key = out.getvalue().strip()

        # Assert it's a non-empty string
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 30)

        # Optional: ensure only allowed characters appear
        self.assertTrue(re.match(r"^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':\",./<>?`~|]+$", key))

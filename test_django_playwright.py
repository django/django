import os
import django
from django.conf import settings
from django.test import LiveServerTestCase
from playwright_adapter import PlaywrightWebDriverAdapter


# Minimal Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test",
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[],
    )

django.setup()


class PlaywrightDjangoTest(LiveServerTestCase):

    def test_homepage(self):
        browser = PlaywrightWebDriverAdapter()
        browser.get(self.live_server_url)
        print("Opened:", self.live_server_url)
        browser.quit()
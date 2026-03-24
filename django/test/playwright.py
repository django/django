# django/test/playwright.py

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError as e:
    raise ImportError(
        "Playwright is required to use PlaywrightTestCase. "
        "Install it with: pip install playwright && playwright install"
    ) from e

from django.conf import settings
from django.test import StaticLiveServerTestCase


class PlaywrightTestCase(StaticLiveServerTestCase):
    """
    Base class for browser integration tests using Playwright.
    Mirrors the API of Django's existing StaticLiveServerTestCase
    so the mental model is familiar to existing contributors.
    
    Usage:
        class MyTest(PlaywrightTestCase):
            def test_something(self):
                self.goto("/some-path/")
                self.assert_text("h1", "Expected Heading")
    """

    browser_name = "chromium"  # overridable: 'firefox' | 'webkit'
    headless = True            # CI default; set False for local debug

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        playwright_settings = getattr(settings, "PLAYWRIGHT", {})
        cls.browser_name = playwright_settings.get("browser", cls.browser_name)
        cls.headless = playwright_settings.get("headless", cls.headless)
        cls._pw = sync_playwright().start()
        cls.browser = getattr(cls._pw, cls.browser_name).launch(
            headless=cls.headless,
            slow_mo=playwright_settings.get("slow_mo", 0),
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()
        super().tearDownClass()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()

    def goto(self, path):
        """Navigate to a path relative to the live server URL."""
        self.page.goto(self.live_server_url + path)

    def assert_text(self, locator, text):
        """Assert that a locator contains the expected text."""
        expect(self.page.locator(locator)).to_have_text(text)

    def login_as(self, user):
        """
        Inject a Django session into the Playwright browser context.
        Avoids going through the login UI — much faster for test setup.
        """
        self.client.force_login(user)
        session_key = self.client.session.session_key
        self.context.add_cookies([{
            "name": settings.SESSION_COOKIE_NAME,
            "value": session_key,
            "url": self.live_server_url,
        }])

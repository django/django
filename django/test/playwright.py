import sys
import unittest
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.test import LiveServerTestCase, override_settings, tag
from django.utils.functional import classproperty
from django.utils.text import capfirst

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class PlaywrightTestCaseBase(type(LiveServerTestCase)):
    # List of browsers to dynamically create test classes for (e.g. chromium, firefox, webkit)
    browsers = ["chromium", "firefox", "webkit"]
    # A Playwright WS endpoint URL to test against.
    playwright_ws_endpoint = None
    # The external host Playwright can reach.
    external_host = None
    # Sentinel value to differentiate browser-specific instances.
    browser = None
    # Run browsers in headless mode.
    headless = False

    def __new__(cls, name, bases, attrs):
        """
        Dynamically create new classes and add them to the test module when
        multiple browsers specs are provided (e.g. --playwright=firefox,chromium).
        """
        test_class = super().__new__(cls, name, bases, attrs)
        # If the test class is either browser-specific or a test base, return it.
        if test_class.browser or not any(
            name.startswith("test") and callable(value) for name, value in attrs.items()
        ):
            return test_class
        elif test_class.browsers:
            # Reuse the created test class to make it browser-specific.
            first_browser = test_class.browsers[0]
            test_class.browser = first_browser
            # Listen on an external interface if using a remote playwright instance.
            host = test_class.host if not test_class.playwright_ws_endpoint else "0.0.0.0"
            test_class.host = host
            test_class.external_host = cls.external_host
            # Create subclasses for each of the remaining browsers and expose
            # them through the test's module namespace.
            module = sys.modules[test_class.__module__]
            for browser in test_class.browsers[1:]:
                browser_test_class = cls.__new__(
                    cls,
                    "%s%s" % (capfirst(browser), name),
                    (test_class,),
                    {
                        "browser": browser,
                        "host": host,
                        "external_host": cls.external_host,
                        "__module__": test_class.__module__,
                    },
                )
                setattr(module, browser_test_class.__name__, browser_test_class)
            return test_class
        # If no browsers were specified, skip this class
        return unittest.skip("No browsers specified.")(test_class)

    # Moved create_playwright_browser to PlaywrightTestCase as a classmethod


class ChangeWindowSize:
    def __init__(self, width, height, page):
        self.page = page
        self.new_size = {"width": width, "height": height}

    def __enter__(self):
        self.old_size = self.page.viewport_size
        self.page.set_viewport_size(self.new_size)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_size:
            self.page.set_viewport_size(self.old_size)


@tag("playwright")
class PlaywrightTestCase(LiveServerTestCase, metaclass=PlaywrightTestCaseBase):
    implicit_wait = 10000  # Playwright default timeout is in milliseconds
    external_host = None
    screenshots = False

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.screenshots:
            return

        for name, func in list(cls.__dict__.items()):
            if not hasattr(func, "_screenshot_cases"):
                continue
            # Remove the main test.
            delattr(cls, name)
            # Add separate tests for each screenshot type.
            for screenshot_case in getattr(func, "_screenshot_cases"):

                @wraps(func)
                def test(self, *args, _func=func, _case=screenshot_case, **kwargs):
                    with getattr(self, _case)():
                        return _func(self, *args, **kwargs)

                test.__name__ = f"{name}_{screenshot_case}"
                test.__qualname__ = f"{test.__qualname__}_{screenshot_case}"
                test._screenshot_name = name
                test._screenshot_case = screenshot_case
                setattr(cls, test.__name__, test)

    @classproperty
    def live_server_url(cls):
        return "http://%s:%s" % (cls.external_host or cls.host, cls.server_thread.port)

    @classproperty
    def allowed_host(cls):
        return cls.external_host or cls.host

    @classmethod
    def create_playwright_browser(cls, playwright):
        if not hasattr(playwright, cls.browser):
            raise ValueError(f"Unsupported browser: {cls.browser}")
        
        browser_type = getattr(playwright, cls.browser)
        
        if cls.playwright_ws_endpoint:
            return browser_type.connect(cls.playwright_ws_endpoint)

        kwargs = {"headless": cls.headless}
        if cls.browser == "chromium":
            kwargs["args"] = ["--disable-infobars"]
            
        return browser_type.launch(**kwargs)

    @classmethod
    def setUpClass(cls):
        if cls.browser not in {"chromium", "firefox", "webkit"}:
            raise unittest.SkipTest(f"Invalid or unsupported browser: {cls.browser}")

        if sync_playwright is None:
            raise unittest.SkipTest(
                "Playwright is not installed. Please install it using `pip install playwright` "
                "and run `playwright install` to download browser binaries."
            )
            
        cls.playwright = sync_playwright().start()
        cls.browser_instance = cls.create_playwright_browser(cls.playwright)
        cls.browser_context = cls.browser_instance.new_context()
        cls.page = cls.browser_context.new_page()
        cls.page.set_default_timeout(cls.implicit_wait)
        super().setUpClass()
        cls.addClassCleanup(cls._quit_playwright)

    @contextmanager
    def desktop_size(self):
        with ChangeWindowSize(1280, 720, self.page):
            yield

    @contextmanager
    def small_screen_size(self):
        with ChangeWindowSize(1024, 768, self.page):
            yield

    @contextmanager
    def mobile_size(self):
        with ChangeWindowSize(360, 800, self.page):
            yield

    @contextmanager
    def rtl(self):
        with self.desktop_size():
            with override_settings(LANGUAGE_CODE=settings.LANGUAGES_BIDI[-1]):
                yield

    @contextmanager
    def dark(self):
        # Navigate to a page before executing a script.
        self.page.goto(self.live_server_url)
        self.page.evaluate("localStorage.setItem('theme', 'dark');")
        with self.desktop_size():
            try:
                yield
            finally:
                self.page.evaluate("localStorage.removeItem('theme');")

    def set_emulated_media(self, *, media=None, features=None):
        if self.browser not in {"chromium", "edge"}:
            self.skipTest(
                "Emulation.setEmulatedMedia is only supported on Chromium and Chrome-based browsers."
            )
        
        kwargs = {}
        if media is not None:
            kwargs["media"] = media
        if features is not None:
            for feature in features:
                if feature.get("name") == "forced-colors":
                    kwargs["forced_colors"] = feature.get("value")

        self.page.emulate_media(**kwargs)

    @contextmanager
    def high_contrast(self):
        self.set_emulated_media(features=[{"name": "forced-colors", "value": "active"}])
        with self.desktop_size():
            try:
                yield
            finally:
                self.set_emulated_media(
                    features=[{"name": "forced-colors", "value": "none"}]
                )

    def take_screenshot(self, name):
        if not self.screenshots:
            return
        test = getattr(self, self._testMethodName)
        filename = f"{test._screenshot_name}--{name}--{test._screenshot_case}.png"
        path = Path.cwd() / "screenshots" / filename
        path.parent.mkdir(exist_ok=True, parents=True)
        self.page.screenshot(path=path)

    def get_browser_logs(self, source=None, level="ALL"):
        """
        Return browser console logs.
        Note: Playwright relies on listeners `page.on("console", callback)`. 
        To collect logs natively, we would need to capture them asynchronously.
        """
        return []

    @classmethod
    def _quit_playwright(cls):
        # Close the page, browser context, browser, and playwright sequentially
        if hasattr(cls, "page"):
            cls.page.close()
        if hasattr(cls, "browser_context"):
            cls.browser_context.close()
        if hasattr(cls, "browser_instance"):
            cls.browser_instance.close()
        if hasattr(cls, "playwright"):
            cls.playwright.stop()

    @contextmanager
    def disable_implicit_wait(self):
        """Disable the default implicit wait."""
        self.page.set_default_timeout(0)
        try:
            yield
        finally:
            self.page.set_default_timeout(self.implicit_wait)


def screenshot_cases(method_names):
    if isinstance(method_names, str):
        method_names = method_names.split(",")

    def wrapper(func):
        func._screenshot_cases = method_names
        setattr(func, "tags", {"screenshot"}.union(getattr(func, "tags", set())))
        return func

    return wrapper

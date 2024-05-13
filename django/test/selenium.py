import sys
import unittest
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.test import LiveServerTestCase, override_settings, tag
from django.utils.functional import classproperty
from django.utils.module_loading import import_string
from django.utils.text import capfirst


class SeleniumTestCaseBase(type(LiveServerTestCase)):
    # List of browsers to dynamically create test classes for.
    browsers = []
    # A selenium hub URL to test against.
    selenium_hub = None
    # The external host Selenium Hub can reach.
    external_host = None
    # Sentinel value to differentiate browser-specific instances.
    browser = None
    # Run browsers in headless mode.
    headless = False

    def __new__(cls, name, bases, attrs):
        """
        Dynamically create new classes and add them to the test module when
        multiple browsers specs are provided (e.g. --selenium=firefox,chrome).
        """
        test_class = super().__new__(cls, name, bases, attrs)
        # If the test class is either browser-specific or a test base, return it.
        if test_class.browser or not any(
            name.startswith("test") and callable(value) for name, value in attrs.items()
        ):
            return test_class
        elif test_class.browsers:
            # Reuse the created test class to make it browser-specific.
            # We can't rename it to include the browser name or create a
            # subclass like we do with the remaining browsers as it would
            # either duplicate tests or prevent pickling of its instances.
            first_browser = test_class.browsers[0]
            test_class.browser = first_browser
            # Listen on an external interface if using a selenium hub.
            host = test_class.host if not test_class.selenium_hub else "0.0.0.0"
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
        # If no browsers were specified, skip this class (it'll still be discovered).
        return unittest.skip("No browsers specified.")(test_class)

    @classmethod
    def import_webdriver(cls, browser):
        return import_string("selenium.webdriver.%s.webdriver.WebDriver" % browser)

    @classmethod
    def import_options(cls, browser):
        return import_string("selenium.webdriver.%s.options.Options" % browser)

    @classmethod
    def get_capability(cls, browser):
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

        return getattr(DesiredCapabilities, browser.upper())

    def create_options(self):
        options = self.import_options(self.browser)()
        if self.headless:
            match self.browser:
                case "chrome" | "edge":
                    options.add_argument("--headless=new")
                case "firefox":
                    options.add_argument("-headless")
        return options

    def create_webdriver(self):
        options = self.create_options()
        if self.selenium_hub:
            from selenium import webdriver

            for key, value in self.get_capability(self.browser).items():
                options.set_capability(key, value)

            return webdriver.Remote(command_executor=self.selenium_hub, options=options)
        return self.import_webdriver(self.browser)(options=options)


class ChangeWindowSize:
    def __init__(self, width, height, selenium):
        self.selenium = selenium
        self.new_size = (width, height)

    def __enter__(self):
        self.old_size = self.selenium.get_window_size()
        self.selenium.set_window_size(*self.new_size)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.selenium.set_window_size(self.old_size["width"], self.old_size["height"])


@tag("selenium")
class SeleniumTestCase(LiveServerTestCase, metaclass=SeleniumTestCaseBase):
    implicit_wait = 10
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
    def setUpClass(cls):
        cls.selenium = cls.create_webdriver()
        cls.selenium.implicitly_wait(cls.implicit_wait)
        super().setUpClass()
        cls.addClassCleanup(cls._quit_selenium)

    @contextmanager
    def desktop_size(self):
        with ChangeWindowSize(1280, 720, self.selenium):
            yield

    @contextmanager
    def small_screen_size(self):
        with ChangeWindowSize(1024, 768, self.selenium):
            yield

    @contextmanager
    def mobile_size(self):
        with ChangeWindowSize(360, 800, self.selenium):
            yield

    @contextmanager
    def rtl(self):
        with self.desktop_size():
            with override_settings(LANGUAGE_CODE=settings.LANGUAGES_BIDI[-1]):
                yield

    @contextmanager
    def dark(self):
        # Navigate to a page before executing a script.
        self.selenium.get(self.live_server_url)
        self.selenium.execute_script("localStorage.setItem('theme', 'dark');")
        with self.desktop_size():
            try:
                yield
            finally:
                self.selenium.execute_script("localStorage.removeItem('theme');")

    def set_emulated_media(self, *, media=None, features=None):
        if self.browser not in {"chrome", "edge"}:
            self.skipTest(
                "Emulation.setEmulatedMedia is only supported on Chromium and "
                "Chrome-based browsers. See https://chromedevtools.github.io/devtools-"
                "protocol/1-3/Emulation/#method-setEmulatedMedia for more details."
            )
        params = {}
        if media is not None:
            params["media"] = media
        if features is not None:
            params["features"] = features

        # Not using .execute_cdp_cmd() as it isn't supported by the remote web driver
        # when using --selenium-hub.
        self.selenium.execute(
            driver_command="executeCdpCommand",
            params={"cmd": "Emulation.setEmulatedMedia", "params": params},
        )

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
        self.selenium.save_screenshot(path)

    @classmethod
    def _quit_selenium(cls):
        # quit() the WebDriver before attempting to terminate and join the
        # single-threaded LiveServerThread to avoid a dead lock if the browser
        # kept a connection alive.
        if hasattr(cls, "selenium"):
            cls.selenium.quit()

    @contextmanager
    def disable_implicit_wait(self):
        """Disable the default implicit wait."""
        self.selenium.implicitly_wait(0)
        try:
            yield
        finally:
            self.selenium.implicitly_wait(self.implicit_wait)


def screenshot_cases(method_names):
    if isinstance(method_names, str):
        method_names = method_names.split(",")

    def wrapper(func):
        func._screenshot_cases = method_names
        setattr(func, "tags", {"screenshot"}.union(getattr(func, "tags", set())))
        return func

    return wrapper

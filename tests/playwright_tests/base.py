import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.test import LiveServerTestCase, override_settings, tag
from django.utils.text import capfirst

PLAYWRIGHT_RECORD_MODES = ("off", "on", "retain-on-failure")


def should_keep_playwright_artifact(mode, failed):
    if mode == "on":
        return True
    if mode == "retain-on-failure":
        return failed
    return False


class PlaywrightTestCaseMeta(type(LiveServerTestCase)):
    # List of browsers to dynamically create test classes for.
    browsers = []
    # Sentinel value to differentiate browser-specific instances.
    browser = None
    # Run browsers with a visible window when True.
    headed = False
    # Delay in milliseconds between Playwright operations.
    slow_mo = 0

    def __new__(cls, name, bases, attrs):
        """
        Dynamically create new classes and add them to the test module when
        multiple browser specs are provided (e.g. --playwright=XXXX).
        """
        test_class = super().__new__(cls, name, bases, attrs)
        # If the test class is either browser-specific or a test base, return
        # it.
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
                        "__module__": test_class.__module__,
                    },
                )
                setattr(module, browser_test_class.__name__, browser_test_class)
            return test_class
        # If no browsers were specified, skip this class (it'll still be
        # discovered).
        return unittest.skip("No browsers specified.")(test_class)

    @classmethod
    def import_browser(cls, browser):
        from playwright.sync_api import Playwright

        if not hasattr(Playwright, browser):
            raise ImportError(
                "Playwright browser specification '%s' is not valid." % browser
            )


class ChangeViewportSize:
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
class PlaywrightTestCase(LiveServerTestCase, metaclass=PlaywrightTestCaseMeta):
    default_timeout = 10000  # milliseconds
    screenshots = False
    tracing = "off"
    video = "off"
    browser_timezone = "America/Chicago"

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

    @classmethod
    def setUpClass(cls):
        # Playwright's sync API leaves an asyncio event loop running on the
        # test thread, which would otherwise raise SynchronousOnlyOperation on
        # ORM use.
        cls._old_async_unsafe = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        cls.addClassCleanup(cls._restore_async_unsafe)

        from playwright.sync_api import expect, sync_playwright

        cls.expect = staticmethod(expect)
        cls._pw = sync_playwright().start()
        cls.addClassCleanup(cls._quit_playwright)

        super().setUpClass()

        browser_type = getattr(cls._pw, cls.browser)
        ignore_default_args = []
        if cls.screenshots:
            ignore_default_args = ["--hide-scrollbars"]
        cls._browser = browser_type.launch(
            headless=not cls.headed,
            slow_mo=cls.slow_mo,
            ignore_default_args=ignore_default_args,
            # unittest.installHandler() in DiscoverRunner already handles
            # SIGINT.
            handle_sigint=False,
        )
        # Use a fixed browser timezone so browser-based tests don't depend on
        # the local timezone of the machine running them.
        context_kwargs = {"timezone_id": cls.browser_timezone}
        if cls.video != "off":
            cls._video_tmpdir = tempfile.TemporaryDirectory(
                prefix="playwright-",
            )
            cls.addClassCleanup(cls._video_tmpdir.cleanup)
            context_kwargs["record_video_dir"] = cls._video_tmpdir.name
        cls._browser_context = cls._browser.new_context(**context_kwargs)
        cls._open_page()
        cls.addClassCleanup(cls._close_browser)

    def setUp(self):
        super().setUp()
        if self.video != "off" and self.page.is_closed():
            # A new page starts a new recording; the previous test closed its
            # page in _save_video.
            type(self)._open_page()
        if self.tracing != "off":
            self._browser_context.tracing.start(
                screenshots=True,
                snapshots=True,
            )
            self.addCleanup(self._stop_tracing)
        if self.video != "off":
            self.addCleanup(self._save_video)

    def _stop_tracing(self):
        if should_keep_playwright_artifact(self.tracing, self._has_failed()):
            path = Path.cwd() / "traces" / self.browser / f"{self._artifact_stem()}.zip"
            path.parent.mkdir(exist_ok=True, parents=True)
            self._browser_context.tracing.stop(path=path)
        else:
            self._browser_context.tracing.stop()

    @classmethod
    def _open_page(cls):
        cls.page = cls._browser_context.new_page()
        cls.page.set_default_timeout(cls.default_timeout)

    def _artifact_stem(self):
        safe_id = "".join("_" if c in '<>:"/\\|?*' else c for c in self.id())
        return safe_id

    def _has_failed(self):
        outcome = getattr(self, "_outcome", None)
        if outcome is None:
            return False
        for _test, exc_info in getattr(outcome, "errors", []):
            if exc_info is not None:
                return True
        result = getattr(outcome, "result", None)
        if result is None:
            return False
        try:
            records = (*result.failures, *result.errors)
        except TypeError:
            return False
        for record in records:
            test = record[0]
            if getattr(test, "test_case", test) is self:
                return True
        return False

    def _save_video(self):
        if self.page.is_closed():
            return
        video = self.page.video
        self.page.close()
        if not video:
            return
        if should_keep_playwright_artifact(self.video, self._has_failed()):
            path = (
                Path.cwd() / "videos" / self.browser / f"{self._artifact_stem()}.webm"
            )
            path.parent.mkdir(exist_ok=True, parents=True)
            video.save_as(path)
        else:
            video.delete()

    @contextmanager
    def desktop_size(self):
        with ChangeViewportSize(1280, 720, self.page):
            yield

    @contextmanager
    def small_screen_size(self):
        with ChangeViewportSize(1024, 768, self.page):
            yield

    @contextmanager
    def mobile_size(self):
        with ChangeViewportSize(360, 800, self.page):
            yield

    @contextmanager
    def rtl(self):
        with self.desktop_size():
            with override_settings(LANGUAGE_CODE=settings.LANGUAGES_BIDI[-1]):
                yield

    @contextmanager
    def dark(self):
        # Navigate to a page before reading/writing storage.
        self.page.goto(self.live_server_url)
        self.page.local_storage.set_item("theme", "dark")
        with self.desktop_size():
            try:
                yield
            finally:
                self.page.local_storage.remove_item("theme")

    @contextmanager
    def high_contrast(self):
        self.page.emulate_media(forced_colors="active")
        with self.desktop_size():
            try:
                yield
            finally:
                self.page.emulate_media(forced_colors="none")

    def take_screenshot(self, name):
        if not self.screenshots:
            return
        test = getattr(self, self._testMethodName)
        filename = f"{test._screenshot_name}--{name}--{test._screenshot_case}.png"
        path = Path.cwd() / "screenshots" / filename
        path.parent.mkdir(exist_ok=True, parents=True)
        self.page.screenshot(path=path)

    @classmethod
    def _close_browser(cls):
        # Close resources before attempting to terminate and join the
        # single-threaded LiveServerThread to avoid a dead lock if the browser
        # kept a connection alive.
        if hasattr(cls, "page"):
            if not cls.page.is_closed():
                cls.page.close()
            del cls.page
        if hasattr(cls, "_browser_context"):
            cls._browser_context.close()
            del cls._browser_context
        if hasattr(cls, "_browser"):
            cls._browser.close()
            del cls._browser

    @classmethod
    def _quit_playwright(cls):
        cls._close_browser()
        if hasattr(cls, "_pw"):
            cls._pw.stop()
            del cls._pw

    @classmethod
    def _restore_async_unsafe(cls):
        if cls._old_async_unsafe is None:
            os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
        else:
            os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = cls._old_async_unsafe


def screenshot_cases(method_names):
    if isinstance(method_names, str):
        method_names = method_names.split(",")

    def wrapper(func):
        func._screenshot_cases = method_names
        setattr(
            func, "tags", {"playwright_screenshot"}.union(getattr(func, "tags", set()))
        )
        return func

    return wrapper

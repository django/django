import sys
import unittest
from contextlib import contextmanager

from django.test import LiveServerTestCase, tag
from django.utils.module_loading import import_string
from django.utils.text import capfirst


class SeleniumTestCaseBase(type(LiveServerTestCase)):
    # List of browsers to dynamically create test classes for.
    browsers = []
    # Sentinel value to differentiate browser-specific instances.
    browser = None

    def __new__(cls, name, bases, attrs):
        """
        Dynamically create new classes and add them to the test module when
        multiple browsers specs are provided (e.g. --selenium=firefox,chrome).
        """
        test_class = super(SeleniumTestCaseBase, cls).__new__(cls, name, bases, attrs)
        # If the test class is either browser-specific or a test base, return it.
        if test_class.browser or not any(name.startswith('test') and callable(value) for name, value in attrs.items()):
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
                    {'browser': browser, '__module__': test_class.__module__}
                )
                setattr(module, browser_test_class.__name__, browser_test_class)
            return test_class
        # If no browsers were specified, skip this class (it'll still be discovered).
        return unittest.skip('No browsers specified.')(test_class)

    @classmethod
    def import_webdriver(cls, browser):
        return import_string("selenium.webdriver.%s.webdriver.WebDriver" % browser)

    def create_webdriver(self):
        return self.import_webdriver(self.browser)()


@tag('selenium')
class SeleniumTestCase(LiveServerTestCase, metaclass=SeleniumTestCaseBase):
    implicit_wait = 10

    @classmethod
    def setUpClass(cls):
        cls.selenium = cls.create_webdriver()
        cls.selenium.implicitly_wait(cls.implicit_wait)
        super(SeleniumTestCase, cls).setUpClass()

    @classmethod
    def _tearDownClassInternal(cls):
        # quit() the WebDriver before attempting to terminate and join the
        # single-threaded LiveServerThread to avoid a dead lock if the browser
        # kept a connection alive.
        if hasattr(cls, 'selenium'):
            cls.selenium.quit()
        super(SeleniumTestCase, cls)._tearDownClassInternal()

    @contextmanager
    def disable_implicit_wait(self):
        """Context manager that disables the default implicit wait."""
        self.selenium.implicitly_wait(0)
        try:
            yield
        finally:
            self.selenium.implicitly_wait(self.implicit_wait)

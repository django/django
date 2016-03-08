from __future__ import unicode_literals

from functools import wraps

from django.test import tag, LiveServerTestCase
from django.utils.module_loading import import_string
from django.utils.six import with_metaclass


def create_browser_test(browser, test):
    @wraps(test)
    def browser_test(self, *args, **kwargs):
        return test(self, *args, **kwargs)
    browser_test.browser = browser
    return browser_test


class SeleniumTestCaseBase(type(LiveServerTestCase)):
    browsers = []

    def __new__(cls, name, bases, attrs):
        for attr, value in list(attrs.items()):
            if attr.startswith('test') and callable(value):
                test = attrs.pop(attr)
                for browser in cls.browsers:
                    attrs[str("test_%s%s" % (browser, attr[4:]))] = create_browser_test(browser, test)
        super_new = super(SeleniumTestCaseBase, cls).__new__
        test_class = super_new(cls, name, bases, attrs)
        test_class.browser_test_classes = {
            browser: super_new(cls, name, (test_class,), {'browser': browser, '__module__': test_class.__module__})
            for browser in cls.browsers
        }
        return test_class

    def __call__(self, method_name):
        method = getattr(self, method_name)
        browser_cls = self.browser_test_classes[method.browser]
        return super(SeleniumTestCaseBase, browser_cls).__call__(method_name)

    def create_webdriver(self):
        return import_string('selenium.webdriver.%s.webdriver.WebDriver' % self.browser)()


@tag('selenium')
class SeleniumTestCase(with_metaclass(SeleniumTestCaseBase, LiveServerTestCase)):

    @classmethod
    def setUpClass(cls):
        super(SeleniumTestCase, cls).setUpClass()
        cls.selenium = cls.create_webdriver()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        super(SeleniumTestCase, cls).tearDownClass()
        cls.selenium.quit()

    def __reduce__(self, *args, **kwargs):
        return self.__class__.__bases__[0], (self._testMethodName,)

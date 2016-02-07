import os
import types
from unittest import skipIf

from six import add_metaclass

from django.test import tag
from django.utils.module_loading import import_string
from django.utils.six import (
    get_function_closure, get_function_code, get_function_defaults,
    get_function_globals,
)


class SeleniumMetaClass(type):

    def __new__(cls, name, bases, attrs):
        """
        Dynamically inject new methods for running tests in different browsers
        when multiple browser specs are provided (e.g. --selenium=firefox,chrome).
        """
        browsers = os.environ.get('DJANGO_SELENIUM_SPECS', '').split(',')
        if browsers[0]:
            for key in list(attrs.keys()):
                if isinstance(attrs[key], types.FunctionType) and key.startswith('test'):
                    method = attrs[key]
                    for index, spec in enumerate(browsers):
                        # Create new methods for browsers other than first one.
                        if index > 0:
                            method_name = '%s__%s' % (key, spec)
                            method = types.FunctionType(
                                get_function_code(method),
                                get_function_globals(method),
                                str(method_name),
                                get_function_defaults(method),
                                get_function_closure(method),
                            )
                            setattr(method, 'browser_spec', spec)
                            attrs[method_name] = method
                        else:
                            setattr(method, 'browser_spec', spec)
        return type.__new__(cls, name, bases, attrs)


skip_selenium = not os.environ.get('DJANGO_SELENIUM_SPECS', '').split(',')[0]


@tag('selenium')
@add_metaclass(SeleniumMetaClass)
@skipIf(skip_selenium, 'Selenium tests not requested.')
class SeleniumTestCaseMixin(object):

    def setUp(self):
        test_method = getattr(self, self._testMethodName)
        browser_spec = test_method.browser_spec
        self.selenium = import_string('selenium.webdriver.%s.webdriver.WebDriver' % browser_spec)()
        self.selenium.implicitly_wait(10)

    def tearDown(self):
        self.selenium.quit()

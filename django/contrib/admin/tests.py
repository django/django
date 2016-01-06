import os
from unittest import SkipTest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import modify_settings
from django.test.selenium import SeleniumHelpers
from django.utils.module_loading import import_string
from django.utils.translation import ugettext as _


class CSPMiddleware(object):
    """The admin's JavaScript should be compatible with CSP."""
    def process_response(self, request, response):
        response['Content-Security-Policy'] = "default-src 'self'"
        return response


@modify_settings(
    MIDDLEWARE_CLASSES={'append': 'django.contrib.admin.tests.CSPMiddleware'},
)
class AdminSeleniumWebDriverTestCase(SeleniumHelpers, StaticLiveServerTestCase):

    available_apps = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
    ]
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'

    @classmethod
    def setUpClass(cls):
        if not os.environ.get('DJANGO_SELENIUM_TESTS', False):
            raise SkipTest('Selenium tests not requested')
        try:
            cls.selenium = import_string(cls.webdriver_class)()
        except Exception as e:
            raise SkipTest('Selenium webdriver "%s" not installed or not '
                           'operational: %s' % (cls.webdriver_class, str(e)))
        # This has to be last to ensure that resources are cleaned up properly!
        super(AdminSeleniumWebDriverTestCase, cls).setUpClass()

    @classmethod
    def _tearDownClassInternal(cls):
        if hasattr(cls, 'selenium'):
            cls.selenium.quit()
        super(AdminSeleniumWebDriverTestCase, cls)._tearDownClassInternal()

    def admin_login(self, username, password, login_url='/admin/'):
        """
        Log into the admin.
        """
        self.selenium.get('%s%s' % (self.live_server_url, login_url))
        username_input = self.selenium.find_element_by_name('username')
        username_input.send_keys(username)
        password_input = self.selenium.find_element_by_name('password')
        password_input.send_keys(password)
        login_text = _('Log in')
        self.selenium.find_element_by_xpath('//input[@value="%s"]' % login_text).click()
        self.wait_page_loaded()

    def get_css_value(self, selector, attribute):
        """
        Return the value for the CSS attribute of an DOM element specified by
        the given selector using the jQuery that ships with admin.
        """
        return self.selenium.execute_script(
            'return django.jQuery("%s").css("%s")' % (selector, attribute)
        )

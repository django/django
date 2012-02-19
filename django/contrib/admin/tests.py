import sys

from django.test import LiveServerTestCase
from django.utils.importlib import import_module
from django.utils.unittest import SkipTest
from django.utils.translation import ugettext as _

class AdminSeleniumWebDriverTestCase(LiveServerTestCase):
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'

    @classmethod
    def setUpClass(cls):
        if sys.version_info < (2, 6):
            raise SkipTest('Selenium Webdriver does not support Python < 2.6.')
        try:
            # Import and start the WebDriver class.
            module, attr = cls.webdriver_class.rsplit('.', 1)
            mod = import_module(module)
            WebDriver = getattr(mod, attr)
            cls.selenium = WebDriver()
        except Exception:
            raise SkipTest('Selenium webdriver "%s" not installed or not '
                           'operational.' % cls.webdriver_class)
        super(AdminSeleniumWebDriverTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(AdminSeleniumWebDriverTestCase, cls).tearDownClass()
        if hasattr(cls, 'selenium'):
            cls.selenium.quit()

    def wait_until(self, callback, timeout=10):
        """
        Helper function that blocks the execution of the tests until the
        specified callback returns a value that is not falsy. This function can
        be called, for example, after clicking a link or submitting a form.
        See the other public methods that call this function for more details.
        """
        from selenium.webdriver.support.wait import WebDriverWait
        WebDriverWait(self.selenium, timeout).until(callback)

    def wait_loaded_tag(self, tag_name, timeout=10):
        """
        Helper function that blocks until the element with the given tag name
        is found on the page.
        """
        self.wait_until(
            lambda driver: driver.find_element_by_tag_name(tag_name),
            timeout
        )

    def admin_login(self, username, password, login_url='/admin/'):
        """
        Helper function to log into the admin.
        """
        self.selenium.get('%s%s' % (self.live_server_url, login_url))
        username_input = self.selenium.find_element_by_name('username')
        username_input.send_keys(username)
        password_input = self.selenium.find_element_by_name('password')
        password_input.send_keys(password)
        login_text = _('Log in')
        self.selenium.find_element_by_xpath(
            '//input[@value="%s"]' % login_text).click()
        # Wait for the next page to be loaded.
        self.wait_loaded_tag('body')

    def get_css_value(self, selector, attribute):
        """
        Helper function that returns the value for the CSS attribute of an
        DOM element specified by the given selector. Uses the jQuery that ships
        with Django.
        """
        return self.selenium.execute_script(
            'return django.jQuery("%s").css("%s")' % (selector, attribute))

    def select_option(self, selector, value):
        """
        Helper function to select the <OPTION> that has the value `value` and
        that is in the <SELECT> widget identified by the CSS selector `selector`.
        """
        from selenium.common.exceptions import NoSuchElementException
        options = self.selenium.find_elements_by_css_selector('%s option' % selector)
        for option in options:
            if option.get_attribute('value') == value:
                option.click()
                return
        raise NoSuchElementException('Option "%s" not found in "%s"' % (value, selector))
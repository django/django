from __future__ import unicode_literals

import os

from django.contrib.admin.tests import AdminSeleniumWebDriverTestCase
from django.test import override_settings

from .models import HTMLTag


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class SeleniumFirefoxTests(AdminSeleniumWebDriverTestCase):

    available_apps = ['admin_messages'] + AdminSeleniumWebDriverTestCase.available_apps
    fixtures = ['admin-views-users.xml']
    urls = "admin_messages.urls"
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'
    screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')

    def test_admin_success_message_code_tag_css(self):
        """
        Ensure that the `<code>` tag is displayed correctly within
        the text of admin success messages. This test case takes
        the screenshot and saves it to the `screenshots` directory.
        """

        self.admin_login(username='super', password='secret')

        self.selenium.get('%s%s' % (self.live_server_url,
            '/admin/admin_messages/htmltag/add/'))

        tag_name_input = self.selenium.find_element_by_xpath('//input[@name="name"]')
        tag_name_input.send_keys('IMG')
        tag_name_input.submit()

        self.wait_page_loaded()

        self.selenium.save_screenshot(os.path.join(self.screenshots_dir,
            'test_admin_success_message_code_tag_css.png'))


class SeleniumChromeTests(SeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.chrome.webdriver.WebDriver'


class SeleniumIETests(SeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.ie.webdriver.WebDriver'

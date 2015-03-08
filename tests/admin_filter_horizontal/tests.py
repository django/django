from __future__ import unicode_literals

import datetime

from selenium.webdriver.common.keys import Keys

from django.contrib.admin.tests import AdminSeleniumWebDriverTestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import override_settings

from .models import Pizza, Topping


class TestDataMixin(object):

    @classmethod
    def setUpTestData(cls):
        # password = "secret"
        User.objects.create(
            pk=100, username='super', first_name='Super', last_name='User', email='super@example.com',
            password='sha1$995a3$6011485ea3834267d719b4c801409b8b1ddd0158', is_active=True, is_superuser=True,
            is_staff=True, last_login=datetime.datetime(2007, 5, 30, 13, 20, 10),
            date_joined=datetime.datetime(2007, 5, 30, 13, 20, 10)
        )


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.SHA1PasswordHasher'],
                   ROOT_URLCONF='admin_filter_horizontal.urls')
class SeleniumFirefoxTests(TestDataMixin, AdminSeleniumWebDriverTestCase):

    available_apps = ['admin_filter_horizontal'] + AdminSeleniumWebDriverTestCase.available_apps
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'

    def setUp(self):
        self.setUpTestData()

        self.peperoni = Topping.objects.create(name='Pepperoni')
        self.cheese = Topping.objects.create(name='Cheese')
        self.mushrooms = Topping.objects.create(name='Mushrooms')

        self.pizza = Pizza.objects.create(name='Pepperoni & Cheese')
        self.pizza.toppings.add(self.peperoni)
        self.pizza.toppings.add(self.cheese)

    def test_browser_refresh(self):
        self.admin_login(username='super', password='secret')
        path = reverse('admin:admin_filter_horizontal_pizza_change', args=(self.pizza.id,))
        self.selenium.get('%s%s' % (self.live_server_url, path))

        inline_id = '#id_toppings_to'
        rows_length = lambda: len(self.selenium.find_elements_by_css_selector('%s.filtered > option' % inline_id))
        self.assertEqual(rows_length(), 2)

        # Refreshing the page with self.selenium.refresh() doesn't demonstrate the problem.
        self.selenium.find_element_by_id('id_toppings_to').send_keys(Keys.F5)

        rows_length = lambda: len(self.selenium.find_elements_by_css_selector('%s.filtered > option' % inline_id))
        self.assertEqual(rows_length(), 2)


class SeleniumChromeTests(SeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.chrome.webdriver.WebDriver'


class SeleniumIETests(SeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.ie.webdriver.WebDriver'

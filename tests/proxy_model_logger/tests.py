from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.test import LiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver

@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class TestProxyModel(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(TestProxyModel, cls).setUpClass()
    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(TestProxyModel, cls).tearDownClass()

    def test_proxy_model_history(self):
        dummy_pass = "django"
        admin_user = User.objects.create_superuser('django', 'user@example.com', dummy_pass)

        self.selenium.get('%s%s' % (self.live_server_url, '/admin/'))
        input = self.selenium.find_element_by_name("username")
        input.send_keys(admin_user.username)

        input = self.selenium.find_element_by_name("password")
        input.send_keys(dummy_pass)
        input.submit()

        self.selenium.get('%s%s' % (self.live_server_url, '/admin/proxy_model_logger/child/add'))
        input = self.selenium.find_element_by_name("name")
        input.send_keys("test")
        input.submit()

        child_content = ContentType.objects.get(app_label="proxy_model_logger", model="child")
        log = LogEntry.objects.latest('id')

        self.assertEqual(log.content_type.id, child_content.id)

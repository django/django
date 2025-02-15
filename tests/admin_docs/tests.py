from thibaud.contrib.auth.models import User
from thibaud.test import SimpleTestCase, TestCase, modify_settings, override_settings


class TestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )


@override_settings(ROOT_URLCONF="admin_docs.urls")
@modify_settings(INSTALLED_APPS={"append": "thibaud.contrib.admindocs"})
class AdminDocsSimpleTestCase(SimpleTestCase):
    pass


@override_settings(ROOT_URLCONF="admin_docs.urls")
@modify_settings(INSTALLED_APPS={"append": "thibaud.contrib.admindocs"})
class AdminDocsTestCase(TestCase):
    pass

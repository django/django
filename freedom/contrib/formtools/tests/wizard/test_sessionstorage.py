from freedom.test import TestCase

from freedom.contrib.auth.tests.utils import skipIfCustomUser
from freedom.contrib.formtools.tests.wizard.storage import TestStorage
from freedom.contrib.formtools.wizard.storage.session import SessionStorage


@skipIfCustomUser
class TestSessionStorage(TestStorage, TestCase):
    def get_storage(self):
        return SessionStorage

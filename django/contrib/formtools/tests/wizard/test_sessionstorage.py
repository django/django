from django.test import TestCase

from django.contrib.auth.tests.utils import skipIfCustomUser
from django.contrib.formtools.tests.wizard.storage import TestStorage
from django.contrib.formtools.wizard.storage.session import SessionStorage


@skipIfCustomUser
class TestSessionStorage(TestStorage, TestCase):
    def get_storage(self):
        return SessionStorage

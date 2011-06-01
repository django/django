from django.test import TestCase

from django.contrib.formtools.wizard.tests.storagetests import TestStorage
from django.contrib.formtools.wizard.storage.session import SessionStorage

class TestSessionStorage(TestStorage, TestCase):
    def get_storage(self):
        return SessionStorage

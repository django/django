from django.shortcuts import make_toast
from django.test import SimpleTestCase


class MakeToastTests(SimpleTestCase):
    def make_toast_test(self):
        self.assertEqual(make_toast(), "toast")




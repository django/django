from django.shortcuts import make_totast  
from django.test import SimpleTestCase

class MakeToastTests(SimpleTestCase):
    def test_make_toast(self):
        self.assertEqual(make_totast(), 'toast')
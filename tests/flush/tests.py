from django.test import TestCase
from django.core.management import call_command
from .models import Restaurant, Address

class FlushCommandTest(TestCase):
    def setUp(self):
        Restaurant.objects.create(name="Jeff's Place")
        Restaurant.objects.create(name="Dotino's")
        Address.objects.create(street="Cool avenue")
        Address.objects.create(street="Cooler avenue")

    def test_flush_clears_all_data(self):
        self.assertEqual(Restaurant.objects.count(), 2)
        call_command("flush", interactive=False)
        self.assertEqual(Restaurant.objects.count(), 0)
        self.assertEqual(Address.objects.count(), 0)

    def test_flush_with_exclude_option(self):
        self.assertEqual(Restaurant.objects.count(), 2)
        self.assertEqual(Address.objects.count(), 2)
        call_command("flush", interactive=False, exclude=["flush_restaurant"])
        self.assertEqual(Restaurant.objects.count(), 2)
        self.assertEqual(Address.objects.count(), 0)

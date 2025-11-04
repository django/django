from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contact.admin import ContactMessageAdmin
from django.contrib.contact.models import ContactMessage
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="contact_tests.urls")
class ContactMessageAdminTest(TestCase):
    """Tests for the ContactMessage admin interface."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        cls.message = ContactMessage.objects.create(
            name="John Doe",
            email="john@example.com",
            message="Test message",
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_contact_message_registered(self):
        """Test that ContactMessage is registered with admin."""
        self.assertIn(ContactMessage, admin.site._registry)

    def test_contact_message_admin_class(self):
        """Test that the correct admin class is used."""
        self.assertIsInstance(
            admin.site._registry[ContactMessage], ContactMessageAdmin
        )

    def test_list_display(self):
        """Test that list_display is configured correctly."""
        admin_instance = admin.site._registry[ContactMessage]
        self.assertEqual(admin_instance.list_display, ["name", "email", "created_at"])

    def test_list_filter(self):
        """Test that list_filter is configured correctly."""
        admin_instance = admin.site._registry[ContactMessage]
        self.assertEqual(admin_instance.list_filter, ["created_at"])

    def test_search_fields(self):
        """Test that search_fields is configured correctly."""
        admin_instance = admin.site._registry[ContactMessage]
        self.assertEqual(admin_instance.search_fields, ["name", "email", "message"])

    def test_readonly_fields(self):
        """Test that all fields are read-only."""
        admin_instance = admin.site._registry[ContactMessage]
        self.assertEqual(
            admin_instance.readonly_fields,
            ["name", "email", "message", "created_at"],
        )

    def test_has_add_permission(self):
        """Test that adding messages through admin is disabled."""
        admin_instance = admin.site._registry[ContactMessage]
        request = type("Request", (), {})()
        self.assertFalse(admin_instance.has_add_permission(request))

    def test_has_change_permission(self):
        """Test that changing messages through admin is disabled."""
        admin_instance = admin.site._registry[ContactMessage]
        request = type("Request", (), {})()
        self.assertFalse(admin_instance.has_change_permission(request))

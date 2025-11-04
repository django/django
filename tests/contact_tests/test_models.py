from django.contrib.contact.models import ContactMessage
from django.test import TestCase
from django.utils import timezone


class ContactMessageModelTest(TestCase):
    """Tests for the ContactMessage model."""

    def test_create_contact_message(self):
        """Test creating a contact message."""
        message = ContactMessage.objects.create(
            name="John Doe",
            email="john@example.com",
            message="This is a test message.",
        )
        self.assertEqual(message.name, "John Doe")
        self.assertEqual(message.email, "john@example.com")
        self.assertEqual(message.message, "This is a test message.")
        self.assertIsNotNone(message.created_at)

    def test_str_representation(self):
        """Test the string representation of a contact message."""
        message = ContactMessage.objects.create(
            name="Jane Smith",
            email="jane@example.com",
            message="Test message",
        )
        expected_str = f"Jane Smith (jane@example.com) - {message.created_at:%Y-%m-%d %H:%M}"
        self.assertEqual(str(message), expected_str)

    def test_ordering(self):
        """Test that contact messages are ordered by created_at descending."""
        message1 = ContactMessage.objects.create(
            name="First",
            email="first@example.com",
            message="First message",
        )
        message2 = ContactMessage.objects.create(
            name="Second",
            email="second@example.com",
            message="Second message",
        )
        messages = ContactMessage.objects.all()
        self.assertEqual(messages[0], message2)
        self.assertEqual(messages[1], message1)

    def test_verbose_names(self):
        """Test that verbose names are set correctly."""
        message = ContactMessage.objects.create(
            name="Test",
            email="test@example.com",
            message="Test",
        )
        self.assertEqual(
            ContactMessage._meta.get_field("name").verbose_name, "name"
        )
        self.assertEqual(
            ContactMessage._meta.get_field("email").verbose_name, "email"
        )
        self.assertEqual(
            ContactMessage._meta.get_field("message").verbose_name, "message"
        )
        self.assertEqual(
            ContactMessage._meta.get_field("created_at").verbose_name, "created at"
        )

    def test_db_table_name(self):
        """Test that the database table name is correct."""
        self.assertEqual(ContactMessage._meta.db_table, "django_contact_message")

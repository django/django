from django.contrib.contact.forms import ContactForm
from django.contrib.contact.models import ContactMessage
from django.test import TestCase


class ContactFormTest(TestCase):
    """Tests for the ContactForm."""

    def test_form_valid_data(self):
        """Test that the form is valid with correct data."""
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "This is a test message.",
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_empty_data(self):
        """Test that the form is invalid with empty data."""
        form = ContactForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 3)
        self.assertIn("name", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("message", form.errors)

    def test_form_missing_name(self):
        """Test that the form is invalid without a name."""
        form_data = {
            "email": "john@example.com",
            "message": "This is a test message.",
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_missing_email(self):
        """Test that the form is invalid without an email."""
        form_data = {
            "name": "John Doe",
            "message": "This is a test message.",
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_missing_message(self):
        """Test that the form is invalid without a message."""
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_form_invalid_email(self):
        """Test that the form is invalid with an invalid email."""
        form_data = {
            "name": "John Doe",
            "email": "not-an-email",
            "message": "This is a test message.",
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_save(self):
        """Test that the form can be saved to create a ContactMessage."""
        form_data = {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "message": "Test save functionality.",
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())
        message = form.save()
        self.assertIsInstance(message, ContactMessage)
        self.assertEqual(message.name, "Jane Smith")
        self.assertEqual(message.email, "jane@example.com")
        self.assertEqual(message.message, "Test save functionality.")

    def test_form_fields_required(self):
        """Test that all fields are required."""
        form = ContactForm()
        self.assertTrue(form.fields["name"].required)
        self.assertTrue(form.fields["email"].required)
        self.assertTrue(form.fields["message"].required)

    def test_form_textarea_widget(self):
        """Test that the message field uses a textarea widget."""
        form = ContactForm()
        self.assertEqual(form.fields["message"].widget.__class__.__name__, "Textarea")

from django.contrib.contact.models import ContactMessage
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="contact_tests.urls")
class ContactViewTest(TestCase):
    """Tests for the contact form view."""

    def test_contact_view_get(self):
        """Test GET request to the contact view."""
        response = self.client.get(reverse("contact:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact/contact_form.html")
        self.assertIn("form", response.context)

    def test_contact_view_post_valid(self):
        """Test POST request with valid data."""
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "This is a test message.",
        }
        response = self.client.post(reverse("contact:contact"), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("contact:thank_you"))
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.first()
        self.assertEqual(message.name, "John Doe")
        self.assertEqual(message.email, "john@example.com")
        self.assertEqual(message.message, "This is a test message.")

    def test_contact_view_post_invalid(self):
        """Test POST request with invalid data."""
        form_data = {
            "name": "",
            "email": "invalid-email",
            "message": "",
        }
        response = self.client.post(reverse("contact:contact"), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact/contact_form.html")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_contact_view_post_missing_data(self):
        """Test POST request with missing required fields."""
        form_data = {"name": "John Doe"}
        response = self.client.post(reverse("contact:contact"), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact/contact_form.html")
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertIn("email", form.errors)
        self.assertIn("message", form.errors)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_contact_view_csrf_token(self):
        """Test that CSRF token is present in the form."""
        response = self.client.get(reverse("contact:contact"))
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_multiple_submissions(self):
        """Test that multiple submissions create multiple messages."""
        form_data1 = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "First message.",
        }
        form_data2 = {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "message": "Second message.",
        }
        self.client.post(reverse("contact:contact"), data=form_data1)
        self.client.post(reverse("contact:contact"), data=form_data2)
        self.assertEqual(ContactMessage.objects.count(), 2)


@override_settings(ROOT_URLCONF="contact_tests.urls")
class ThankYouViewTest(TestCase):
    """Tests for the thank you page view."""

    def test_thank_you_view_get(self):
        """Test GET request to the thank you view."""
        response = self.client.get(reverse("contact:thank_you"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact/thank_you.html")

    def test_thank_you_view_contains_link_back(self):
        """Test that the thank you page contains a link back to contact form."""
        response = self.client.get(reverse("contact:thank_you"))
        self.assertContains(response, reverse("contact:contact"))

    def test_thank_you_view_direct_access(self):
        """Test that thank you page can be accessed directly."""
        response = self.client.get(reverse("contact:thank_you"))
        self.assertEqual(response.status_code, 200)

from django.contrib import auth
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase


class TestLogin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="password")

    def setUp(self):
        self.request = HttpRequest()
        self.request.session = self.client.session

    def test_user_login(self):
        auth.login(self.request, self.user)
        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        auth.login(self.request, self.user)
        self.assertEqual(self.request.session[auth.SESSION_KEY], str(self.user.pk))

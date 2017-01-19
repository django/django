from unittest import mock

from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db import connections
from django.test import TestCase, override_settings
from django.urls import reverse


class Router:
    target_db = None

    def db_for_read(self, model, **hints):
        return self.target_db

    db_for_write = db_for_read


site = admin.AdminSite(name='test_adminsite')
site.register(User, admin_class=UserAdmin)

urlpatterns = [
    url(r'^admin/', site.urls),
]


@override_settings(ROOT_URLCONF=__name__, DATABASE_ROUTERS=['%s.Router' % __name__])
class MultiDatabaseTests(TestCase):
    multi_db = True

    @classmethod
    def setUpTestData(cls):
        cls.superusers = {}
        for db in connections:
            Router.target_db = db
            cls.superusers[db] = User.objects.create_superuser(
                username='admin', password='something', email='test@test.org',
            )

    @mock.patch('django.contrib.auth.admin.transaction')
    def test_add_view(self, mock):
        for db in connections:
            Router.target_db = db
            self.client.force_login(self.superusers[db])
            self.client.post(reverse('test_adminsite:auth_user_add'), {
                'username': 'some_user',
                'password1': 'helloworld',
                'password2': 'helloworld',
            })
            mock.atomic.assert_called_with(using=db)

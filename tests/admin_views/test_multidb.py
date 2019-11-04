from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.db import connections
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .models import Book


class Router:
    target_db = None

    def db_for_read(self, model, **hints):
        return self.target_db

    db_for_write = db_for_read


site = admin.AdminSite(name='test_adminsite')
site.register(Book)

urlpatterns = [
    path('admin/', site.urls),
]


@override_settings(ROOT_URLCONF=__name__, DATABASE_ROUTERS=['%s.Router' % __name__])
class MultiDatabaseTests(TestCase):
    databases = {'default', 'other'}

    @classmethod
    def setUpTestData(cls):
        cls.superusers = {}
        cls.test_book_ids = {}
        for db in connections:
            Router.target_db = db
            cls.superusers[db] = User.objects.create_superuser(
                username='admin', password='something', email='test@test.org',
            )
            b = Book(name='Test Book')
            b.save(using=db)
            cls.test_book_ids[db] = b.id

    @mock.patch('django.contrib.admin.options.transaction')
    def test_add_view(self, mock):
        for db in connections:
            with self.subTest(db=db):
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                self.client.post(
                    reverse('test_adminsite:admin_views_book_add'),
                    {'name': 'Foobar: 5th edition'},
                )
                mock.atomic.assert_called_with(using=db)

    @mock.patch('django.contrib.admin.options.transaction')
    def test_change_view(self, mock):
        for db in connections:
            with self.subTest(db=db):
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                self.client.post(
                    reverse('test_adminsite:admin_views_book_change', args=[self.test_book_ids[db]]),
                    {'name': 'Test Book 2: Test more'},
                )
                mock.atomic.assert_called_with(using=db)

    @mock.patch('django.contrib.admin.options.transaction')
    def test_delete_view(self, mock):
        for db in connections:
            with self.subTest(db=db):
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                self.client.post(
                    reverse('test_adminsite:admin_views_book_delete', args=[self.test_book_ids[db]]),
                    {'post': 'yes'},
                )
                mock.atomic.assert_called_with(using=db)

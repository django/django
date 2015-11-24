from __future__ import unicode_literals

import datetime

from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.test.client import RequestFactory

from .models import Article

site = admin.AdminSite(name="test_adminsite")
site.register(User)
site.register(Article)

urlpatterns = [
    url(r'^test_admin/admin/', site.urls),
]


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.SHA1PasswordHasher'],
    ROOT_URLCONF="admin_views.test_adminsite",
)
class SiteEachContextTest(TestCase):
    """
    Check each_context contains the documented variables and that available_apps context
    variable structure is the expected one.
    """
    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create(
            password='sha1$995a3$6011485ea3834267d719b4c801409b8b1ddd0158',
            last_login=datetime.datetime(2007, 5, 30, 13, 20, 10), is_superuser=True, username='super',
            first_name='Super', last_name='User', email='super@example.com',
            is_staff=True, is_active=True, date_joined=datetime.datetime(2007, 5, 30, 13, 20, 10),
        )

    def setUp(self):
        factory = RequestFactory()
        request = factory.get(reverse('test_adminsite:index'))
        request.user = self.u1
        self.ctx = site.each_context(request)

    def test_each_context(self):
        ctx = self.ctx
        self.assertEqual(ctx['site_header'], 'Django administration')
        self.assertEqual(ctx['site_title'], 'Django site admin')
        self.assertEqual(ctx['site_url'], '/')
        self.assertEqual(ctx['has_permission'], True)

    def test_available_apps(self):
        ctx = self.ctx
        apps = ctx['available_apps']
        # we have registered two models from two different apps
        self.assertEqual(len(apps), 2)

        # admin_views.Article
        admin_views = apps[0]
        self.assertEqual(admin_views['app_label'], 'admin_views')
        self.assertEqual(len(admin_views['models']), 1)
        self.assertEqual(admin_views['models'][0]['object_name'], 'Article')

        # auth.User
        auth = apps[1]
        self.assertEqual(auth['app_label'], 'auth')
        self.assertEqual(len(auth['models']), 1)
        user = auth['models'][0]
        self.assertEqual(user['object_name'], 'User')

        self.assertEqual(auth['app_url'], '/test_admin/admin/auth/')
        self.assertEqual(auth['has_module_perms'], True)

        self.assertIn('perms', user)
        self.assertEqual(user['perms']['add'], True)
        self.assertEqual(user['perms']['change'], True)
        self.assertEqual(user['perms']['delete'], True)
        self.assertEqual(user['admin_url'], '/test_admin/admin/auth/user/')
        self.assertEqual(user['add_url'], '/test_admin/admin/auth/user/add/')
        self.assertEqual(user['name'], 'Users')

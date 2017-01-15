# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import management
from django.test import TransactionTestCase, override_settings


@override_settings(
    MIGRATION_MODULES=dict(settings.MIGRATION_MODULES,
                           permissions_tests='permissions_tests.operations_migrations'),
)
class PermissionsOperationsTests(TransactionTestCase):
    available_apps = [
        'permissions_tests',
        'django.contrib.contenttypes',
        'django.contrib.auth',
    ]

    def test_migrate(self):
        management.call_command(
            'migrate', 'permissions_tests', '0002', '--fake', database='default',
            interactive=False, verbosity=0,
        )
        management.call_command(
            'migrate', 'permissions_tests', '0001', database='default',
            interactive=False, verbosity=0,
        )
        management.call_command(
            'migrate', 'permissions_tests', '0002', database='default',
            interactive=False, verbosity=0,
        )
        ct = ContentType.objects.filter(app_label='permissions_tests', model='foo').get()
        self.assertTrue(Permission.objects.filter(content_type=ct).exists())
        self.assertEqual(Permission.objects.filter(content_type=ct).first().name, "Can add Bar")
        management.call_command(
            'migrate', 'permissions_tests', '0001', database='default',
            interactive=False, verbosity=0,
        )
        self.assertTrue(Permission.objects.filter(content_type=ct).exists())
        self.assertEqual(Permission.objects.filter(content_type=ct).first().name, "Can add Foo")
        management.call_command(
            'migrate', 'permissions_tests', 'zero', database='default',
            interactive=False, verbosity=0,
        )

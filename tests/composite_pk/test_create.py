import unittest

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Tenant, User


class CompositePKCreateTests(TestCase):
    """
    Test the .create(), .save(), .bulk_create(), .get_or_create() methods of
    composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()

    @unittest.skipUnless(connection.vendor == "sqlite", "SQLite specific test")
    def test_create_user_in_sqlite(self):
        test_cases = [
            ({"tenant": self.tenant, "id": 2412}, 2412),
            ({"tenant_id": self.tenant.id, "id": 5316}, 5316),
            ({"pk": (self.tenant.id, 7424)}, 7424),
        ]

        for fields, user_id in test_cases:
            with self.subTest(fields=fields, user_id=user_id):
                with CaptureQueriesContext(connection) as context:
                    obj = User.objects.create(**fields)

                self.assertEqual(obj.tenant_id, self.tenant.id)
                self.assertEqual(obj.id, user_id)
                self.assertEqual(obj.pk, (self.tenant.id, user_id))
                self.assertEqual(len(context.captured_queries), 1)
                u = User._meta.db_table
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'INSERT INTO "{u}" ("tenant_id", "id") '
                    f"VALUES ({self.tenant.id}, {user_id})",
                )

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific test")
    def test_create_user_in_postgresql(self):
        test_cases = [
            ({"tenant": self.tenant, "id": 5231}, 5231),
            ({"tenant_id": self.tenant.id, "id": 6123}, 6123),
            ({"pk": (self.tenant.id, 3513)}, 3513),
        ]

        for fields, user_id in test_cases:
            with self.subTest(fields=fields, user_id=user_id):
                with CaptureQueriesContext(connection) as context:
                    obj = User.objects.create(**fields)

                self.assertEqual(obj.tenant_id, self.tenant.id)
                self.assertEqual(obj.id, user_id)
                self.assertEqual(obj.pk, (self.tenant.id, user_id))
                self.assertEqual(len(context.captured_queries), 1)
                u = User._meta.db_table
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'INSERT INTO "{u}" ("tenant_id", "id") '
                    f"VALUES ({self.tenant.id}, {user_id}) "
                    f'RETURNING "{u}"."id"',
                )

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific test")
    def test_create_user_with_autofield_in_postgresql(self):
        test_cases = [
            {"tenant": self.tenant},
            {"tenant_id": self.tenant.id},
        ]

        for fields in test_cases:
            with CaptureQueriesContext(connection) as context:
                obj = User.objects.create(**fields)

            self.assertEqual(obj.tenant_id, self.tenant.id)
            self.assertIsInstance(obj.id, int)
            self.assertGreater(obj.id, 0)
            self.assertEqual(obj.pk, (self.tenant.id, obj.id))
            self.assertEqual(len(context.captured_queries), 1)
            u = User._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'INSERT INTO "{u}" ("tenant_id") '
                f"VALUES ({self.tenant.id}) "
                f'RETURNING "{u}"."id"',
            )

    def test_save_user(self):
        user = User(tenant=self.tenant, id=9241)
        user.save()
        self.assertEqual(user.tenant_id, self.tenant.id)
        self.assertEqual(user.tenant, self.tenant)
        self.assertEqual(user.id, 9241)
        self.assertEqual(user.pk, (self.tenant.id, 9241))

    @unittest.skipUnless(connection.vendor == "sqlite", "SQLite specific test")
    def test_bulk_create_users_in_sqlite(self):
        objs = [
            User(tenant=self.tenant, id=8291),
            User(tenant_id=self.tenant.id, id=4021),
            User(pk=(self.tenant.id, 8214)),
        ]

        with CaptureQueriesContext(connection) as context:
            result = User.objects.bulk_create(objs)

        obj_1, obj_2, obj_3 = result
        self.assertEqual(obj_1.tenant_id, self.tenant.id)
        self.assertEqual(obj_1.id, 8291)
        self.assertEqual(obj_1.pk, (obj_1.tenant_id, obj_1.id))
        self.assertEqual(obj_2.tenant_id, self.tenant.id)
        self.assertEqual(obj_2.id, 4021)
        self.assertEqual(obj_2.pk, (obj_2.tenant_id, obj_2.id))
        self.assertEqual(obj_3.tenant_id, self.tenant.id)
        self.assertEqual(obj_3.id, 8214)
        self.assertEqual(obj_3.pk, (obj_3.tenant_id, obj_3.id))
        self.assertEqual(len(context.captured_queries), 1)
        u = User._meta.db_table
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'INSERT INTO "{u}" ("tenant_id", "id") '
            f"VALUES ({self.tenant.id}, 8291), ({self.tenant.id}, 4021), "
            f"({self.tenant.id}, 8214)",
        )

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific test")
    def test_bulk_create_users_in_postgresql(self):
        objs = [
            User(tenant=self.tenant, id=8361),
            User(tenant_id=self.tenant.id, id=2819),
            User(pk=(self.tenant.id, 9136)),
            User(tenant=self.tenant),
            User(tenant_id=self.tenant.id),
        ]

        with CaptureQueriesContext(connection) as context:
            result = User.objects.bulk_create(objs)

        obj_1, obj_2, obj_3, obj_4, obj_5 = result
        self.assertEqual(obj_1.tenant_id, self.tenant.id)
        self.assertEqual(obj_1.id, 8361)
        self.assertEqual(obj_1.pk, (obj_1.tenant_id, obj_1.id))
        self.assertEqual(obj_2.tenant_id, self.tenant.id)
        self.assertEqual(obj_2.id, 2819)
        self.assertEqual(obj_2.pk, (obj_2.tenant_id, obj_2.id))
        self.assertEqual(obj_3.tenant_id, self.tenant.id)
        self.assertEqual(obj_3.id, 9136)
        self.assertEqual(obj_3.pk, (obj_3.tenant_id, obj_3.id))
        self.assertEqual(obj_4.tenant_id, self.tenant.id)
        self.assertIsInstance(obj_4.id, int)
        self.assertGreater(obj_4.id, 0)
        self.assertEqual(obj_4.pk, (obj_4.tenant_id, obj_4.id))
        self.assertEqual(obj_5.tenant_id, self.tenant.id)
        self.assertIsInstance(obj_5.id, int)
        self.assertGreater(obj_5.id, obj_4.id)
        self.assertEqual(obj_5.pk, (obj_5.tenant_id, obj_5.id))
        self.assertEqual(len(context.captured_queries), 2)
        u = User._meta.db_table
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'INSERT INTO "{u}" ("tenant_id", "id") '
            f"VALUES ({self.tenant.id}, 8361), ({self.tenant.id}, 2819), "
            f"({self.tenant.id}, 9136) "
            f'RETURNING "{u}"."id"',
        )
        self.assertEqual(
            context.captured_queries[1]["sql"],
            f'INSERT INTO "{u}" ("tenant_id") '
            f"VALUES ({self.tenant.id}), ({self.tenant.id}) "
            f'RETURNING "{u}"."id"',
        )

    def test_get_or_create_user_by_pk(self):
        user, created = User.objects.get_or_create(pk=(self.tenant.id, 8314))

        self.assertTrue(created)
        self.assertEqual(1, User.objects.all().count())
        self.assertEqual(user.pk, (self.tenant.id, 8314))
        self.assertEqual(user.tenant_id, self.tenant.id)
        self.assertEqual(user.id, 8314)

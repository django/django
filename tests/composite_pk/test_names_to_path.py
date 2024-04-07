from django.db.models.query_utils import PathInfo
from django.db.models.sql import Query
from django.test import TestCase

from .models import Comment, Tenant, User


class NamesToPathTests(TestCase):
    def test_id(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(["id"], User._meta)

        self.assertEqual(path, [])
        self.assertEqual(final_field, User._meta.get_field("id"))
        self.assertEqual(targets, (User._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_pk(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(["pk"], User._meta)

        self.assertEqual(path, [])
        self.assertEqual(final_field, User._meta.get_field("pk"))
        self.assertEqual(targets, (User._meta.get_field("pk"),))
        self.assertEqual(rest, [])

    def test_tenant_id(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(
            ["tenant", "id"], User._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=User._meta,
                    to_opts=Tenant._meta,
                    target_fields=(Tenant._meta.get_field("id"),),
                    join_field=User._meta.get_field("tenant"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, Tenant._meta.get_field("id"))
        self.assertEqual(targets, (Tenant._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_user_id(self):
        query = Query(Comment)
        path, final_field, targets, rest = query.names_to_path(
            ["user", "id"], Comment._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=Comment._meta,
                    to_opts=User._meta,
                    target_fields=(
                        User._meta.get_field("tenant"),
                        User._meta.get_field("id"),
                    ),
                    join_field=Comment._meta.get_field("user"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, User._meta.get_field("id"))
        self.assertEqual(targets, (User._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_user_tenant_id(self):
        query = Query(Comment)
        path, final_field, targets, rest = query.names_to_path(
            ["user", "tenant", "id"], Comment._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=Comment._meta,
                    to_opts=User._meta,
                    target_fields=(
                        User._meta.get_field("tenant"),
                        User._meta.get_field("id"),
                    ),
                    join_field=Comment._meta.get_field("user"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
                PathInfo(
                    from_opts=User._meta,
                    to_opts=Tenant._meta,
                    target_fields=(Tenant._meta.get_field("id"),),
                    join_field=User._meta.get_field("tenant"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, Tenant._meta.get_field("id"))
        self.assertEqual(targets, (Tenant._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_comments(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(["comments"], User._meta)

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=User._meta,
                    to_opts=Comment._meta,
                    target_fields=(Comment._meta.get_field("pk"),),
                    join_field=User._meta.get_field("comments"),
                    m2m=True,
                    direct=False,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, User._meta.get_field("comments"))
        self.assertEqual(targets, (Comment._meta.get_field("pk"),))
        self.assertEqual(rest, [])

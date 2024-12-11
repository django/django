from datetime import date, datetime
from unittest import skipIf
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db import connection
from django.db.models import Count
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Comment, Dummy, Post, Tag, Tenant, User


class CompositePKGenericTests(TestCase):
    POST_1_ID = "e1516ac0-4469-4306-b0ac-2c435e677aa4"
    DUMMY_1_UUID = "81598d5a-fa03-4800-bae4-823ca12824d5"
    DUMMY_2_UUID = "ac567f4c-9b6e-4770-86a6-1abf071a2958"

    @classmethod
    def setUpTestData(cls):
        cls.dummy_1 = Dummy.objects.create(
            small_integer=32767,
            integer=2147483647,
            big_integer=9223372036854775807,
            datetime=datetime(2024, 11, 30, 6, 26, 1),
            date=date(2024, 11, 30),
            uuid=UUID(cls.DUMMY_1_UUID),
            char="薑戈",
        )
        cls.dummy_2 = Dummy.objects.create(
            small_integer=-32768,
            integer=-2147483648,
            big_integer=-9223372036854775808,
            datetime=datetime(2024, 12, 8, 1, 2, 3),
            date=date(2024, 12, 8),
            uuid=UUID(cls.DUMMY_2_UUID),
            char="😊",
        )
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1,
            id=1,
            email="user0001@example.com",
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_1,
            id=2,
            email="user0002@example.com",
        )
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_1)
        cls.post_1 = Post.objects.create(tenant=cls.tenant_1, id=UUID(cls.POST_1_ID))
        cls.comment_1_tag = Tag.objects.create(
            name="comment_1", content_object=cls.comment_1
        )
        cls.post_1_tag = Tag.objects.create(name="post_1", content_object=cls.post_1)
        cls.dummy_1_tag = Tag.objects.create(name="dummy_1", content_object=cls.dummy_1)
        cls.dummy_2_tag = Tag.objects.create(name="dummy_2", content_object=cls.dummy_2)
        cls.comment_ct = ContentType.objects.get_for_model(Comment)
        cls.post_ct = ContentType.objects.get_for_model(Post)
        cls.dummy_ct = ContentType.objects.get_for_model(Dummy)
        cls.post_1_fk = f'[{cls.tenant_1.id}, "{cls.POST_1_ID}"]'
        cls.comment_1_fk = f"[{cls.tenant_1.id}, {cls.comment_1.id}]"
        cls.dummy_1_fk = (
            '[32767, 2147483647, 9223372036854775807, "2024-11-30T06:26:01", '
            f'"2024-11-30", "{cls.DUMMY_1_UUID}", "\\u8591\\u6208"]'
        )
        cls.dummy_2_fk = (
            '[-32768, -2147483648, -9223372036854775808, "2024-12-08T01:02:03", '
            f'"2024-12-08", "{cls.DUMMY_2_UUID}", "\\ud83d\\ude0a"]'
        )

    def test_fields(self):
        self.assertEqual(self.comment_1_tag.content_type, self.comment_ct)
        self.assertEqual(self.comment_1_tag.object_id, self.comment_1_fk)
        self.assertEqual(self.comment_1_tag.content_object, self.comment_1)

        self.assertEqual(self.post_1_tag.content_type, self.post_ct)
        self.assertEqual(self.post_1_tag.object_id, self.post_1_fk)
        self.assertEqual(self.post_1_tag.content_object, self.post_1)

        self.assertEqual(self.dummy_1_tag.content_type, self.dummy_ct)
        self.assertEqual(self.dummy_1_tag.object_id, self.dummy_1_fk)
        self.assertEqual(self.dummy_1_tag.content_object, self.dummy_1)

        self.assertEqual(self.dummy_2_tag.content_type, self.dummy_ct)
        self.assertEqual(self.dummy_2_tag.object_id, self.dummy_2_fk)
        self.assertEqual(self.dummy_2_tag.content_object, self.dummy_2)

        self.assertSequenceEqual(self.post_1.tags.all(), (self.post_1_tag,))
        self.assertSequenceEqual(self.dummy_1.tags.all(), (self.dummy_1_tag,))
        self.assertSequenceEqual(self.dummy_2.tags.all(), (self.dummy_2_tag,))

    def test_fields_before_save(self):
        comment = Comment(pk=(1, 2))
        tag = Tag(content_object=comment)
        self.assertEqual(tag.object_id, "[1, 2]")
        comment.id = 3
        self.assertEqual(tag.object_id, "[1, 2]")

    def test_cascade_delete_if_generic_relation(self):
        Post.objects.get(pk=self.post_1.pk).delete()
        self.assertFalse(Tag.objects.filter(pk=self.post_1_tag.pk).exists())

        Dummy.objects.get(pk=self.dummy_1.pk).delete()
        self.assertFalse(Tag.objects.filter(pk=self.dummy_1_tag.pk).exists())

    def test_no_cascade_delete_if_no_generic_relation(self):
        Comment.objects.get(pk=self.comment_1.pk).delete()
        comment_1_tag = Tag.objects.get(pk=self.comment_1_tag.pk)
        self.assertIsNone(comment_1_tag.content_object)

    def test_tags_clear(self):
        post_1 = Post.objects.get(pk=self.post_1.pk)
        post_1.tags.clear()
        self.assertEqual(post_1.tags.count(), 0)
        self.assertFalse(Tag.objects.filter(pk=self.post_1_tag.pk).exists())

        dummy_1 = Dummy.objects.get(pk=self.dummy_1.pk)
        dummy_1.tags.clear()
        self.assertEqual(dummy_1.tags.count(), 0)
        self.assertFalse(Tag.objects.filter(pk=self.dummy_1_tag.pk).exists())

    def test_tags_remove(self):
        post_1 = Post.objects.get(pk=self.post_1.pk)
        post_1.tags.remove(self.post_1_tag)
        self.assertEqual(post_1.tags.count(), 0)
        self.assertFalse(Tag.objects.filter(pk=self.post_1_tag.pk).exists())

        dummy_1 = Dummy.objects.get(pk=self.dummy_1.pk)
        dummy_1.tags.remove(self.dummy_1_tag)
        self.assertEqual(dummy_1.tags.count(), 0)
        self.assertFalse(Tag.objects.filter(pk=self.dummy_1_tag.pk).exists())

    def test_tags_create(self):
        tag_count = Tag.objects.count()

        post_1 = Post.objects.get(pk=self.post_1.pk)
        post_1.tags.create(name="foo")
        self.assertEqual(post_1.tags.count(), 2)
        self.assertEqual(Tag.objects.count(), tag_count + 1)

        tag = Tag.objects.get(name="foo")
        self.assertEqual(tag.content_type, self.post_ct)
        self.assertEqual(tag.object_id, self.post_1_fk)
        self.assertEqual(tag.content_object, post_1)

    def test_tags_add(self):
        tag_count = Tag.objects.count()
        post_1 = Post.objects.get(pk=self.post_1.pk)

        tag_1 = Tag(name="foo")
        post_1.tags.add(tag_1, bulk=False)
        self.assertEqual(post_1.tags.count(), 2)
        self.assertEqual(Tag.objects.count(), tag_count + 1)

        tag_1 = Tag.objects.get(name="foo")
        self.assertEqual(tag_1.content_type, self.post_ct)
        self.assertEqual(tag_1.object_id, self.post_1_fk)
        self.assertEqual(tag_1.content_object, post_1)

        tag_2 = Tag.objects.create(name="bar", content_object=self.comment_2)
        post_1.tags.add(tag_2)
        self.assertEqual(post_1.tags.count(), 3)
        self.assertEqual(Tag.objects.count(), tag_count + 2)

        tag_2 = Tag.objects.get(name="bar")
        self.assertEqual(tag_2.content_type, self.post_ct)
        self.assertEqual(tag_2.object_id, self.post_1_fk)
        self.assertEqual(tag_2.content_object, post_1)

    def test_tags_set(self):
        tag_count = Tag.objects.count()
        comment_1_tag = Tag.objects.get(name=self.comment_1_tag.name)
        post_1 = Post.objects.get(pk=self.post_1.pk)
        post_1.tags.set([comment_1_tag])
        self.assertEqual(post_1.tags.count(), 1)
        self.assertEqual(Tag.objects.count(), tag_count - 1)
        self.assertFalse(Tag.objects.filter(pk=self.post_1_tag.pk).exists())

    def test_tags_get_or_create(self):
        post_1 = Post.objects.get(pk=self.post_1.pk)

        tag_1, created = post_1.tags.get_or_create(name=self.post_1_tag.name)
        self.assertFalse(created)
        self.assertEqual(tag_1.pk, self.post_1_tag.pk)
        self.assertEqual(tag_1.content_type, self.post_ct)
        self.assertEqual(tag_1.object_id, self.post_1_fk)
        self.assertEqual(tag_1.content_object, post_1)

        tag_2, created = post_1.tags.get_or_create(name="foo")
        self.assertTrue(created)
        self.assertEqual(tag_2.content_type, self.post_ct)
        self.assertEqual(tag_2.object_id, self.post_1_fk)
        self.assertEqual(tag_2.content_object, post_1)

    def test_tags_update_or_create(self):
        post_1 = Post.objects.get(pk=self.post_1.pk)

        tag_1, created = post_1.tags.update_or_create(
            name=self.post_1_tag.name, defaults={"name": "foo"}
        )
        self.assertFalse(created)
        self.assertEqual(tag_1.pk, self.post_1_tag.pk)
        self.assertEqual(tag_1.name, "foo")
        self.assertEqual(tag_1.content_type, self.post_ct)
        self.assertEqual(tag_1.object_id, self.post_1_fk)
        self.assertEqual(tag_1.content_object, post_1)

        tag_2, created = post_1.tags.update_or_create(name="bar")
        self.assertTrue(created)
        self.assertEqual(tag_2.content_type, self.post_ct)
        self.assertEqual(tag_2.object_id, self.post_1_fk)
        self.assertEqual(tag_2.content_object, post_1)

    def test_filter_by_related_query_name(self):
        self.assertSequenceEqual(
            Tag.objects.filter(post__id=self.post_1.id), (self.post_1_tag,)
        )
        self.assertSequenceEqual(
            Tag.objects.filter(dummy__big_integer=self.dummy_1.big_integer),
            (self.dummy_1_tag,),
        )

    @skipIf(
        connection.vendor == "mysql" and connection.mysql_is_mariadb,
        "MariaDB's JSON_UNQUOTE doesn't support surrogate pairs "
        "(https://jira.mariadb.org/browse/MDEV-21124)",
    )
    def test_aggregate(self):
        with self.subTest("Post"):
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(
                    Post.objects.aggregate(Count("tags")),
                    {"tags__count": 1},
                    ctx[-1]["sql"],
                )
        with self.subTest("Dummy"):
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(
                    Dummy.objects.aggregate(Count("tags")),
                    {"tags__count": 2},
                    ctx[-1]["sql"],
                )

    def test_generic_prefetch(self):
        tags = Tag.objects.prefetch_related(
            GenericPrefetch(
                "content_object",
                [
                    Post.objects.all(),
                    Comment.objects.all(),
                    Dummy.objects.all(),
                ],
            )
        ).order_by("pk")

        self.assertEqual(len(tags), 4)
        self.assertEqual(tags[0], self.comment_1_tag)
        self.assertEqual(tags[1], self.post_1_tag)
        self.assertEqual(tags[2], self.dummy_1_tag)

        with self.assertNumQueries(0):
            self.assertEqual(tags[0].content_object, self.comment_1)
        with self.assertNumQueries(0):
            self.assertEqual(tags[1].content_object, self.post_1)
        with self.assertNumQueries(0):
            self.assertEqual(tags[2].content_object, self.dummy_1)
        with self.assertNumQueries(0):
            self.assertEqual(tags[3].content_object, self.dummy_2)

    def test_to_json(self):
        field = Post._meta.pk
        self.assertEqual(
            field.to_json((1, "004bc28c-a085-44ca-a823-747dcf4ddfd3")),
            '[1, "004bc28c-a085-44ca-a823-747dcf4ddfd3"]',
        )
        self.assertEqual(
            field.to_json((2, UUID("a5a626e5-d34a-4197-94ea-83547029d6ed"))),
            '[2, "a5a626e5-d34a-4197-94ea-83547029d6ed"]',
        )

    def test_to_json_length_mismatch(self):
        field = Post._meta.pk
        msg = "CompositePrimaryKey has 2 fields but it tried to serialize %s."
        with self.assertRaisesMessage(ValueError, msg % 1):
            self.assertIsNone(field.to_json((1,)))
        with self.assertRaisesMessage(ValueError, msg % 3):
            self.assertIsNone(field.to_json((1, 2, 3)))

    def test_from_json(self):
        field = Post._meta.pk
        self.assertEqual(
            field.from_json('[1, "cb6b99bc-66b0-497f-bafe-193b90af6296"]'),
            (1, UUID("cb6b99bc-66b0-497f-bafe-193b90af6296")),
        )
        self.assertEqual(
            field.from_json('[2, "1d5c63dda5264a12a2ec929d51e04430"]'),
            (2, UUID("1d5c63dd-a526-4a12-a2ec-929d51e04430")),
        )

    def test_from_json_length_mismatch(self):
        field = Post._meta.pk
        msg = (
            "CompositePrimaryKey has 2 fields but it tried to deserialize %s. "
            "Did you change the CompositePrimaryKey fields and forgot to "
            'update the related GenericForeignKey "object_id" fields?'
        )
        with self.assertRaisesMessage(ValueError, msg % 1):
            self.assertIsNone(field.from_json("[1]"))
        with self.assertRaisesMessage(ValueError, msg % 3):
            self.assertIsNone(field.from_json("[1, 2, 3]"))

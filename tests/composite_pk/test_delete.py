from django.test import TestCase

from .models import Comment, Tenant, User


class CompositePKDeleteTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1,
            id=1,
            email="user0001@example.com",
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_2,
            id=2,
            email="user0002@example.com",
        )
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_2)
        cls.comment_3 = Comment.objects.create(id=3, user=cls.user_2)

    def test_delete_tenant_by_pk(self):
        result = Tenant.objects.filter(pk=self.tenant_1.pk).delete()

        self.assertEqual(
            result,
            (
                3,
                {
                    "composite_pk.Comment": 1,
                    "composite_pk.User": 1,
                    "composite_pk.Tenant": 1,
                },
            ),
        )

        self.assertIs(Tenant.objects.filter(pk=self.tenant_1.pk).exists(), False)
        self.assertIs(Tenant.objects.filter(pk=self.tenant_2.pk).exists(), True)
        self.assertIs(User.objects.filter(pk=self.user_1.pk).exists(), False)
        self.assertIs(User.objects.filter(pk=self.user_2.pk).exists(), True)
        self.assertIs(Comment.objects.filter(pk=self.comment_1.pk).exists(), False)
        self.assertIs(Comment.objects.filter(pk=self.comment_2.pk).exists(), True)
        self.assertIs(Comment.objects.filter(pk=self.comment_3.pk).exists(), True)

    def test_delete_user_by_pk(self):
        result = User.objects.filter(pk=self.user_1.pk).delete()

        self.assertEqual(
            result, (2, {"composite_pk.User": 1, "composite_pk.Comment": 1})
        )

        self.assertIs(User.objects.filter(pk=self.user_1.pk).exists(), False)
        self.assertIs(User.objects.filter(pk=self.user_2.pk).exists(), True)
        self.assertIs(Comment.objects.filter(pk=self.comment_1.pk).exists(), False)
        self.assertIs(Comment.objects.filter(pk=self.comment_2.pk).exists(), True)
        self.assertIs(Comment.objects.filter(pk=self.comment_3.pk).exists(), True)

    def test_delete_comments_by_user(self):
        result = Comment.objects.filter(user=self.user_2).delete()

        self.assertEqual(result, (2, {"composite_pk.Comment": 2}))

        self.assertIs(Comment.objects.filter(pk=self.comment_1.pk).exists(), True)
        self.assertIs(Comment.objects.filter(pk=self.comment_2.pk).exists(), False)
        self.assertIs(Comment.objects.filter(pk=self.comment_3.pk).exists(), False)

    def test_delete_without_pk(self):
        msg = (
            "Comment object can't be deleted because its pk attribute is set "
            "to None."
        )

        with self.assertRaisesMessage(ValueError, msg):
            Comment().delete()
        with self.assertRaisesMessage(ValueError, msg):
            Comment(tenant_id=1).delete()
        with self.assertRaisesMessage(ValueError, msg):
            Comment(id=1).delete()

from django.test import TestCase

from .models import Comment, Tenant, User


class CompositePKDeleteTests(TestCase):
    """
    Test the .delete(), .exists() methods of composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.user_1 = User.objects.create(tenant=cls.tenant_1, id=1)
        cls.user_2 = User.objects.create(tenant=cls.tenant_2, id=2)
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

        self.assertFalse(Tenant.objects.filter(pk=self.tenant_1.pk).exists())
        self.assertTrue(Tenant.objects.filter(pk=self.tenant_2.pk).exists())
        self.assertFalse(User.objects.filter(pk=self.user_1.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.user_2.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.comment_1.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.comment_2.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.comment_3.pk).exists())

    def test_delete_user_by_pk(self):
        result = User.objects.filter(pk=self.user_1.pk).delete()

        self.assertEqual(
            result, (2, {"composite_pk.User": 1, "composite_pk.Comment": 1})
        )

        self.assertFalse(User.objects.filter(pk=self.user_1.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.user_2.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.comment_1.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.comment_2.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.comment_3.pk).exists())

    def test_delete_comments_by_user(self):
        result = Comment.objects.filter(user=self.user_2).delete()

        self.assertEqual(result, (2, {"composite_pk.Comment": 2}))

        self.assertTrue(Comment.objects.filter(pk=self.comment_1.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.comment_2.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.comment_3.pk).exists())

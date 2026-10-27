from django.db.models import prefetch_related_objects
from django.test import TestCase
from django.utils.deprecation import RemovedInDjango2029Warning

from .models import Comment, Tenant, User


class CompositePKNewInstanceTests(TestCase):
    deprecation_msg = (
        "Passing a newly constructed model instance to related filters is "
        "deprecated. Pass target field values instead."
    )

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(id=7)
        cls.user = User.objects.create(tenant=cls.tenant, id=1, email="a@example.com")
        cls.other = User.objects.create(tenant=cls.tenant, id=2, email="b@example.com")
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)
        cls.other_comment = Comment.objects.create(
            tenant=cls.tenant, id=2, user=cls.other
        )

    def new_user(self):
        return User(tenant_id=self.tenant.pk, id=self.user.id)

    def test_filter_new_instance(self):
        obj = self.new_user()
        self.assertIs(obj._state.adding, True)
        for method in ("filter", "exclude"):
            expected = [self.comment] if method == "filter" else [self.other_comment]
            for lookup in ("user", "user__in"):
                with self.subTest(method=method, lookup=lookup):
                    value = [obj] if lookup.endswith("__in") else obj
                    with (
                        self.assertNumQueries(0),
                        self.assertWarnsMessage(
                            RemovedInDjango2029Warning, self.deprecation_msg
                        ) as warning,
                    ):
                        qs = getattr(Comment.objects, method)(**{lookup: value})
                    self.assertEqual(warning.filename, __file__)
                    self.assertSequenceEqual(qs, expected)

    def test_filter_target_values(self):
        self.assertSequenceEqual(
            Comment.objects.filter(user=self.user.pk), [self.comment]
        )
        self.assertSequenceEqual(
            Comment.objects.filter(user=tuple(reversed(self.user.pk))), []
        )

    def test_contains_new_instance(self):
        msg = (
            "Passing a newly constructed model instance to QuerySet.contains() "
            "is deprecated. Use filter(pk=obj.pk).exists() instead."
        )
        for evaluated in (False, True):
            with self.subTest(evaluated=evaluated):
                qs = User.objects.all()
                if evaluated:
                    list(qs)
                with (
                    self.assertNumQueries(0 if evaluated else 1),
                    self.assertWarnsMessage(RemovedInDjango2029Warning, msg) as warning,
                ):
                    self.assertIs(qs.contains(self.new_user()), True)
                self.assertEqual(warning.filename, __file__)

    def test_reverse_manager_new_instance(self):
        with self.assertNumQueries(1):
            self.assertSequenceEqual(self.new_user().comments.all(), [self.comment])

    def test_prefetch_new_instance(self):
        obj = self.new_user()
        with self.assertNumQueries(1):
            prefetch_related_objects([obj], "comments")
        with self.assertNumQueries(0):
            self.assertSequenceEqual(obj.comments.all(), [self.comment])

    def test_delete_new_instance(self):
        self.new_user().delete()
        self.assertSequenceEqual(Comment.objects.all(), [self.other_comment])

from operator import attrgetter
from unittest.mock import Mock

from django.db import models
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps

from .base_tests import BaseOrderWithRespectToTests
from .models import Answer, Dimension, Entity, Post, Question


class OrderWithRespectToBaseTests(BaseOrderWithRespectToTests, TestCase):
    Answer = Answer
    Post = Post
    Question = Question


class OrderWithRespectToDatabaseTests(TestCase):
    databases = {"default", "other"}

    @classmethod
    def setUpTestData(cls):
        for database, order in (("default", [1, 2, 3]), ("other", [2, 3, 1])):
            question = Question.objects.using(database).create(pk=1, text=database)
            for pk in order:
                Answer.objects.using(database).create(
                    pk=pk, text=f"{database}-{pk}", question=question
                )

    def test_previous_and_next_database(self):
        for database, pk, previous, next_ in (
            ("default", 2, 1, 3),
            ("other", 3, 2, 1),
        ):
            answer = Answer.objects.using(database).get(pk=pk)
            for method, expected_pk in (
                ("get_previous_in_order", previous),
                ("get_next_in_order", next_),
            ):
                with self.subTest(database=database, method=method):
                    unused_database = "other" if database == "default" else "default"
                    with (
                        self.assertNumQueries(1, using=database),
                        self.assertNumQueries(0, using=unused_database),
                    ):
                        neighbor = getattr(answer, method)()
                    self.assertEqual(neighbor.text, f"{database}-{expected_pk}")
                    self.assertEqual(neighbor._state.db, database)

    def test_previous_and_next_router_hints(self):
        for source_database, routed_database in (("other", None), ("default", "other")):
            answer = Answer.objects.using(source_database).get(pk=3)
            for method, expected_pk in (
                ("get_previous_in_order", 2),
                ("get_next_in_order", 1),
            ):
                with self.subTest(source_database=source_database, method=method):
                    router = Mock()
                    router.db_for_read.return_value = routed_database
                    with (
                        self.settings(DATABASE_ROUTERS=[router]),
                        self.assertNumQueries(1, using="other"),
                        self.assertNumQueries(0, using="default"),
                    ):
                        neighbor = getattr(answer, method)()
                    self.assertEqual(neighbor.text, f"other-{expected_pk}")
                    self.assertEqual(neighbor._state.db, "other")
                    router.db_for_read.assert_called_once_with(Answer, instance=answer)
                    self.assertIs(
                        router.db_for_read.call_args.kwargs["instance"], answer
                    )


class OrderWithRespectToTests(SimpleTestCase):
    @isolate_apps("order_with_respect_to")
    def test_duplicate_order_field(self):
        class Bar(models.Model):
            class Meta:
                app_label = "order_with_respect_to"

        class Foo(models.Model):
            bar = models.ForeignKey(Bar, models.CASCADE)
            order = models.OrderWrt()

            class Meta:
                order_with_respect_to = "bar"
                app_label = "order_with_respect_to"

        count = 0
        for field in Foo._meta.local_fields:
            if isinstance(field, models.OrderWrt):
                count += 1

        self.assertEqual(count, 1)


class TestOrderWithRespectToOneToOnePK(TestCase):
    def test_set_order(self):
        e = Entity.objects.create()
        d = Dimension.objects.create(entity=e)
        c1 = d.component_set.create()
        c2 = d.component_set.create()
        d.set_component_order([c1.id, c2.id])
        self.assertQuerySetEqual(
            d.component_set.all(), [c1.id, c2.id], attrgetter("pk")
        )

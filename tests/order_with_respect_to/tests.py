from operator import attrgetter

from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps

from .base_tests import BaseOrderWithRespectToTests
from .models import Answer, Dimension, Entity, Post, Question


class OrderWithRespectToBaseTests(BaseOrderWithRespectToTests, TestCase):
    Answer = Answer
    Post = Post
    Question = Question


class OrderWithRespectToTests(TestCase):

    @isolate_apps('order_with_respect_to')
    def test_duplicate_order_field(self):
        class Bar(models.Model):
            class Meta:
                app_label = 'order_with_respect_to'

        class Foo(models.Model):
            bar = models.ForeignKey(Bar, models.CASCADE)
            order = models.OrderWrt()

            class Meta:
                order_with_respect_to = 'bar'
                app_label = 'order_with_respect_to'

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
        self.assertQuerysetEqual(d.component_set.all(), [c1.id, c2.id], attrgetter('pk'))

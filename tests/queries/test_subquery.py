from django.test import TestCase

from .models import NamedCategory, Tag


class TestSubquery(TestCase):
    def test_simple_subquery(self):
        c1 = NamedCategory(name="c1")
        c2 = NamedCategory(name="c2")
        c1.save()
        c2.save()
        t1 = Tag(name="t11", category=c1)
        t2 = Tag(name="t12", category=c1)
        t3 = Tag(name="t21", category=c2)
        t4 = Tag(name="t22", category=c2)
        t1.save()
        t2.save()
        t3.save()
        t4.save()

        qs1 = Tag.objects.exclude(name__startswith="t11").as_subquery()
        self.assertEqual(qs1.count(), 3)
        qs2 = qs1.filter(name__startswith="t2")
        self.assertEqual(qs2.count(), 2)

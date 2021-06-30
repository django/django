from datetime import datetime, timedelta

from mango.db.models.functions import Now
from mango.test import TestCase
from mango.utils import timezone

from ..models import Article

lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua."""


class NowTests(TestCase):

    def test_basic(self):
        a1 = Article.objects.create(
            title='How to Mango',
            text=lorem_ipsum,
            written=timezone.now(),
        )
        a2 = Article.objects.create(
            title='How to Time Travel',
            text=lorem_ipsum,
            written=timezone.now(),
        )
        num_updated = Article.objects.filter(id=a1.id, published=None).update(published=Now())
        self.assertEqual(num_updated, 1)
        num_updated = Article.objects.filter(id=a1.id, published=None).update(published=Now())
        self.assertEqual(num_updated, 0)
        a1.refresh_from_db()
        self.assertIsInstance(a1.published, datetime)
        a2.published = Now() + timedelta(days=2)
        a2.save()
        a2.refresh_from_db()
        self.assertIsInstance(a2.published, datetime)
        self.assertQuerysetEqual(
            Article.objects.filter(published__lte=Now()),
            ['How to Mango'],
            lambda a: a.title
        )
        self.assertQuerysetEqual(
            Article.objects.filter(published__gt=Now()),
            ['How to Time Travel'],
            lambda a: a.title
        )

from datetime import datetime, timedelta

from django.db.models.functions import Now
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import Article

lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua."""


class NowTests(TestCase):

    def test_basic(self):
        a1 = Article.objects.create(
            title='How to Django',
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
            ['How to Django'],
            lambda a: a.title
        )
        self.assertQuerysetEqual(
            Article.objects.filter(published__gt=Now()),
            ['How to Time Travel'],
            lambda a: a.title
        )

    def compare_db_and_py_now(self):
        a = Article.objects.create(
            written=timezone.now(),
            published=Now(),
        )

        # Some debug printing, should not be part of the final testcase
        import django.conf
        import django.db
        a.refresh_from_db()
        print(self.id())
        print("TIME_ZONE:", django.conf.settings.TIME_ZONE, "connection:", django.db.connection.timezone_name)
        if django.db.connection.settings_dict.get('ENGINE', False) == 'django.db.backends.mysql':
            with django.db.connection.cursor() as cursor:
                cursor.execute("SELECT @@global.time_zone, @@session.time_zone, @@system_time_zone;")
                row = cursor.fetchone()
                print("global.time_zone:", row[0], "session.time_zone", row[1], "system_time_zone:", row[2])
        print("now:", timezone.now(), "written:", a.written, "published:", a.published)
        print()

        # Check that both written and published are within one minute of now for both Now() and timezone.now()
        self.assertSequenceEqual(Article.objects.filter(published__lte=Now() + timedelta(minutes=1)), [a])
        self.assertSequenceEqual(Article.objects.filter(written__lte=Now() + timedelta(minutes=1)), [a])
        self.assertSequenceEqual(Article.objects.filter(published__gt=Now() - timedelta(minutes=1)), [a])
        self.assertSequenceEqual(Article.objects.filter(written__gt=Now() - timedelta(minutes=1)), [a])

        self.assertSequenceEqual(Article.objects.filter(published__lte=timezone.now() + timedelta(minutes=1)), [a])
        self.assertSequenceEqual(Article.objects.filter(written__lte=timezone.now() + timedelta(minutes=1)), [a])
        self.assertSequenceEqual(Article.objects.filter(published__gt=timezone.now() - timedelta(minutes=1)), [a])
        self.assertSequenceEqual(Article.objects.filter(written__gt=timezone.now() - timedelta(minutes=1)), [a])

    @override_settings(USE_TZ=False)
    def test_without_use_tz(self):
        self.compare_db_and_py_now()

    @override_settings(USE_TZ=True)
    def test_with_use_tz(self):
        self.compare_db_and_py_now()

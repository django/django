from datetime import datetime

from django.test import TestCase

from .models import Article, Reporter, Writer


class M2MIntermediaryTests(TestCase):
    def test_intermediary(self):
        r1 = Reporter.objects.create(first_name="John", last_name="Smith")
        r2 = Reporter.objects.create(first_name="Jane", last_name="Doe")

        a = Article.objects.create(
            headline="This is a test", pub_date=datetime(2005, 7, 27)
        )

        w1 = Writer.objects.create(reporter=r1, article=a, position="Main writer")
        w2 = Writer.objects.create(reporter=r2, article=a, position="Contributor")

        self.assertQuerySetEqual(
            a.writer_set.select_related().order_by("-position"),
            [
                ("John Smith", "Main writer"),
                ("Jane Doe", "Contributor"),
            ],
            lambda w: (str(w.reporter), w.position),
        )
        self.assertEqual(w1.reporter, r1)
        self.assertEqual(w2.reporter, r2)

        self.assertEqual(w1.article, a)
        self.assertEqual(w2.article, a)

        self.assertQuerySetEqual(
            r1.writer_set.all(),
            [("John Smith", "Main writer")],
            lambda w: (str(w.reporter), w.position),
        )

    def test_intermediary_delete(self):
        r = Reporter.objects.create(first_name="Alice", last_name="Brown")
        a = Article.objects.create(
            headline="Delete test", pub_date=datetime(2023, 1, 1)
        )
        w = Writer.objects.create(reporter=r, article=a, position="Editor")
        w.delete()
        self.assertEqual(a.writer_set.count(), 0)

    def test_intermediary_update(self):
        r = Reporter.objects.create(first_name="Bob", last_name="Green")
        a = Article.objects.create(
            headline="Update test", pub_date=datetime(2023, 2, 1)
        )
        w = Writer.objects.create(reporter=r, article=a, position="Junior")
        w.position = "Senior"
        w.save()
        w.refresh_from_db()
        self.assertEqual(w.position, "Senior")

    def test_intermediary_str(self):
        r = Reporter.objects.create(first_name="Carol", last_name="White")
        self.assertEqual(str(r), "Carol White")

    def test_multiple_articles_per_reporter(self):
        r = Reporter.objects.create(first_name="Dan", last_name="Black")
        a1 = Article.objects.create(headline="Article 1", pub_date=datetime(2023, 3, 1))
        a2 = Article.objects.create(headline="Article 2", pub_date=datetime(2023, 3, 2))
        Writer.objects.create(reporter=r, article=a1, position="Writer")
        Writer.objects.create(reporter=r, article=a2, position="Writer")
        self.assertEqual(r.writer_set.count(), 2)

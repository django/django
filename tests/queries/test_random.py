from django.test import TestCase

from .models import Author, ExtraInfo


class RandomTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        extra = ExtraInfo.objects.create(info="e1", value=1)
        cls.authors = [
            Author.objects.create(name="a%d" % i, num=i, extra=extra)
            for i in range(10)
        ]

    def test_random(self):
        # Basic functionality
        self.assertEqual(len(Author.objects.random(5)), 5)
        self.assertEqual(len(Author.objects.random(10)), 10)

        # Test default count=1
        self.assertEqual(len(Author.objects.random()), 1)

        # Ensure random order (statistically likely for 10 items)
        # Note: This is non-deterministic but highly probable.
        # Running it multiple times should yield different results.
        list(Author.objects.random(5))
        list(Author.objects.random(5))
        # It's possible but unlikely they are identical.
        # We mainly want to ensure it works without error.

    def test_random_count_error(self):
        msg = "Count must be at least 1."
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.random(0)
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.random(-1)

    def test_random_sliced_error(self):
        msg = "Cannot use random() on a sliced queryset."
        with self.assertRaisesMessage(TypeError, msg):
            Author.objects.all()[:5].random(2)

    def test_random_with_filters(self):
        # Should respect filters
        qs = Author.objects.filter(num__lt=5).random(3)
        self.assertEqual(len(qs), 3)
        for author in qs:
            self.assertLess(author.num, 5)

    def test_random_exceeds_count(self):
        # Requesting more than exists should return all
        qs = Author.objects.filter(num__lt=2).random(5)
        self.assertEqual(len(qs), 2)

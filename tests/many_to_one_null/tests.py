from django.test import TestCase

from .models import Article, Car, Driver, Reporter


class ManyToOneNullTests(TestCase):
    def setUp(self):
        # Create a Reporter.
        self.r = Reporter(name='John Smith')
        self.r.save()
        # Create an Article.
        self.a = Article(headline="First", reporter=self.r)
        self.a.save()
        # Create an Article via the Reporter object.
        self.a2 = self.r.article_set.create(headline="Second")
        # Create an Article with no Reporter by passing "reporter=None".
        self.a3 = Article(headline="Third", reporter=None)
        self.a3.save()
        # Create another article and reporter
        self.r2 = Reporter(name='Paul Jones')
        self.r2.save()
        self.a4 = self.r2.article_set.create(headline='Fourth')

    def test_get_related(self):
        self.assertEqual(self.a.reporter.id, self.r.id)
        # Article objects have access to their related Reporter objects.
        r = self.a.reporter
        self.assertEqual(r.id, self.r.id)

    def test_created_via_related_set(self):
        self.assertEqual(self.a2.reporter.id, self.r.id)

    def test_related_set(self):
        # Reporter objects have access to their related Article objects.
        self.assertQuerysetEqual(self.r.article_set.all(), ['<Article: First>', '<Article: Second>'])
        self.assertQuerysetEqual(self.r.article_set.filter(headline__startswith='Fir'), ['<Article: First>'])
        self.assertEqual(self.r.article_set.count(), 2)

    def test_created_without_related(self):
        self.assertIsNone(self.a3.reporter)
        # Need to reget a3 to refresh the cache
        a3 = Article.objects.get(pk=self.a3.pk)
        with self.assertRaises(AttributeError):
            getattr(a3.reporter, 'id')
        # Accessing an article's 'reporter' attribute returns None
        # if the reporter is set to None.
        self.assertIsNone(a3.reporter)
        # To retrieve the articles with no reporters set, use "reporter__isnull=True".
        self.assertQuerysetEqual(Article.objects.filter(reporter__isnull=True), ['<Article: Third>'])
        # We can achieve the same thing by filtering for the case where the
        # reporter is None.
        self.assertQuerysetEqual(Article.objects.filter(reporter=None), ['<Article: Third>'])
        # Set the reporter for the Third article
        self.assertQuerysetEqual(self.r.article_set.all(), ['<Article: First>', '<Article: Second>'])
        self.r.article_set.add(a3)
        self.assertQuerysetEqual(
            self.r.article_set.all(),
            ['<Article: First>', '<Article: Second>', '<Article: Third>']
        )
        # Remove an article from the set, and check that it was removed.
        self.r.article_set.remove(a3)
        self.assertQuerysetEqual(self.r.article_set.all(), ['<Article: First>', '<Article: Second>'])
        self.assertQuerysetEqual(Article.objects.filter(reporter__isnull=True), ['<Article: Third>'])

    def test_remove_from_wrong_set(self):
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Fourth>'])
        # Try to remove a4 from a set it does not belong to
        with self.assertRaises(Reporter.DoesNotExist):
            self.r.article_set.remove(self.a4)
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Fourth>'])

    def test_set(self):
        # Use manager.set() to allocate ForeignKey. Null is legal, so existing
        # members of the set that are not in the assignment set are set to null.
        self.r2.article_set.set([self.a2, self.a3])
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Second>', '<Article: Third>'])
        # Use manager.set(clear=True)
        self.r2.article_set.set([self.a3, self.a4], clear=True)
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Fourth>', '<Article: Third>'])
        # Clear the rest of the set
        self.r2.article_set.set([])
        self.assertQuerysetEqual(self.r2.article_set.all(), [])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__isnull=True),
            ['<Article: Fourth>', '<Article: Second>', '<Article: Third>']
        )

    def test_assign_clear_related_set(self):
        # Use descriptor assignment to allocate ForeignKey. Null is legal, so
        # existing members of the set that are not in the assignment set are
        # set to null.
        self.r2.article_set.set([self.a2, self.a3])
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Second>', '<Article: Third>'])
        # Clear the rest of the set
        self.r.article_set.clear()
        self.assertQuerysetEqual(self.r.article_set.all(), [])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__isnull=True),
            ['<Article: First>', '<Article: Fourth>']
        )

    def test_assign_with_queryset(self):
        # Querysets used in reverse FK assignments are pre-evaluated
        # so their value isn't affected by the clearing operation in
        # RelatedManager.set() (#19816).
        self.r2.article_set.set([self.a2, self.a3])

        qs = self.r2.article_set.filter(headline="Second")
        self.r2.article_set.set(qs)

        self.assertEqual(1, self.r2.article_set.count())
        self.assertEqual(1, qs.count())

    def test_add_efficiency(self):
        r = Reporter.objects.create()
        articles = []
        for _ in range(3):
            articles.append(Article.objects.create())
        with self.assertNumQueries(1):
            r.article_set.add(*articles)
        self.assertEqual(r.article_set.count(), 3)

    def test_clear_efficiency(self):
        r = Reporter.objects.create()
        for _ in range(3):
            r.article_set.create()
        with self.assertNumQueries(1):
            r.article_set.clear()
        self.assertEqual(r.article_set.count(), 0)

    def test_related_null_to_field(self):
        c1 = Car.objects.create()
        d1 = Driver.objects.create()
        self.assertIs(d1.car, None)
        with self.assertNumQueries(0):
            self.assertEqual(list(c1.drivers.all()), [])

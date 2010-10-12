from django.test import TestCase
from models import Reporter, Article

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
        self.assertQuerysetEqual(self.r.article_set.all(),
                                 ['<Article: First>', '<Article: Second>'])
        self.assertQuerysetEqual(self.r.article_set.filter(headline__startswith='Fir'),
                                 ['<Article: First>'])
        self.assertEqual(self.r.article_set.count(), 2)

    def test_created_without_related(self):
        self.assertEqual(self.a3.reporter, None)
        # Need to reget a3 to refresh the cache
        a3 = Article.objects.get(pk=3)
        self.assertRaises(AttributeError, getattr, a3.reporter, 'id')
        # Accessing an article's 'reporter' attribute returns None
        # if the reporter is set to None.
        self.assertEqual(a3.reporter, None)
        # To retrieve the articles with no reporters set, use "reporter__isnull=True".
        self.assertQuerysetEqual(Article.objects.filter(reporter__isnull=True),
                                 ['<Article: Third>'])
        # We can achieve the same thing by filtering for the case where the
        # reporter is None.
        self.assertQuerysetEqual(Article.objects.filter(reporter=None),
                                 ['<Article: Third>'])
        # Set the reporter for the Third article
        self.assertQuerysetEqual(self.r.article_set.all(),
            ['<Article: First>', '<Article: Second>'])
        self.r.article_set.add(a3)
        self.assertQuerysetEqual(self.r.article_set.all(),
            ['<Article: First>', '<Article: Second>', '<Article: Third>'])
        # Remove an article from the set, and check that it was removed.
        self.r.article_set.remove(a3)
        self.assertQuerysetEqual(self.r.article_set.all(),
                                 ['<Article: First>', '<Article: Second>'])
        self.assertQuerysetEqual(Article.objects.filter(reporter__isnull=True),
                                 ['<Article: Third>'])

    def test_remove_from_wrong_set(self):
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Fourth>'])
        # Try to remove a4 from a set it does not belong to
        self.assertRaises(Reporter.DoesNotExist, self.r.article_set.remove, self.a4)
        self.assertQuerysetEqual(self.r2.article_set.all(), ['<Article: Fourth>'])

    def test_assign_clear_related_set(self):
        # Use descriptor assignment to allocate ForeignKey. Null is legal, so
        # existing members of set that are not in the assignment set are set null
        self.r2.article_set = [self.a2, self.a3]
        self.assertQuerysetEqual(self.r2.article_set.all(),
                                 ['<Article: Second>', '<Article: Third>'])
        # Clear the rest of the set
        self.r.article_set.clear()
        self.assertQuerysetEqual(self.r.article_set.all(), [])
        self.assertQuerysetEqual(Article.objects.filter(reporter__isnull=True),
                                 ['<Article: First>', '<Article: Fourth>'])

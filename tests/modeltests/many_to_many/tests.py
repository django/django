from __future__ import absolute_import

from django.test import TestCase
from django.utils import six

from .models import Article, Publication


class ManyToManyTests(TestCase):

    def setUp(self):
        # Create a couple of Publications.
        self.p1 = Publication.objects.create(id=None, title='The Python Journal')
        self.p2 = Publication.objects.create(id=None, title='Science News')
        self.p3 = Publication.objects.create(id=None, title='Science Weekly')
        self.p4 = Publication.objects.create(title='Highlights for Children')

        self.a1 = Article.objects.create(id=None, headline='Django lets you build Web apps easily')
        self.a1.publications.add(self.p1)

        self.a2 = Article.objects.create(id=None, headline='NASA uses Python')
        self.a2.publications.add(self.p1, self.p2, self.p3, self.p4)

        self.a3 = Article.objects.create(headline='NASA finds intelligent life on Earth')
        self.a3.publications.add(self.p2)

        self.a4 = Article.objects.create(headline='Oxygen-free diet works wonders')
        self.a4.publications.add(self.p2)

    def test_add(self):
        # Create an Article.
        a5 = Article(id=None, headline='Django lets you reate Web apps easily')
        # You can't associate it with a Publication until it's been saved.
        self.assertRaises(ValueError, getattr, a5, 'publications')
        # Save it!
        a5.save()
        # Associate the Article with a Publication.
        a5.publications.add(self.p1)
        self.assertQuerysetEqual(a5.publications.all(),
                                 ['<Publication: The Python Journal>'])
        # Create another Article, and set it to appear in both Publications.
        a6 = Article(id=None, headline='ESA uses Python')
        a6.save()
        a6.publications.add(self.p1, self.p2)
        a6.publications.add(self.p3)
        # Adding a second time is OK
        a6.publications.add(self.p3)
        self.assertQuerysetEqual(a6.publications.all(),
            [
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])

        # Adding an object of the wrong type raises TypeError
        with six.assertRaisesRegex(self, TypeError, "'Publication' instance expected, got <Article.*"):
            a6.publications.add(a5)
        # Add a Publication directly via publications.add by using keyword arguments.
        p4 = a6.publications.create(title='Highlights for Adults')
        self.assertQuerysetEqual(a6.publications.all(),
            [
                '<Publication: Highlights for Adults>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])

    def test_reverse_add(self):
        # Adding via the 'other' end of an m2m
        a5 = Article(headline='NASA finds intelligent life on Mars')
        a5.save()
        self.p2.article_set.add(a5)
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA finds intelligent life on Mars>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(a5.publications.all(),
                                 ['<Publication: Science News>'])

        # Adding via the other end using keywords
        new_article = self.p2.article_set.create(headline='Carbon-free diet works wonders')
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: Carbon-free diet works wonders>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA finds intelligent life on Mars>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        a6 = self.p2.article_set.all()[3]
        self.assertQuerysetEqual(a6.publications.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])

    def test_related_sets(self):
        # Article objects have access to their related Publication objects.
        self.assertQuerysetEqual(self.a1.publications.all(),
             ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(self.a2.publications.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])
        # Publication objects have access to their related Article objects.
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(self.p1.article_set.all(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(Publication.objects.get(id=self.p4.id).article_set.all(),
                                 ['<Article: NASA uses Python>'])

    def test_selects(self):
        # We can perform kwarg queries across m2m relationships
        self.assertQuerysetEqual(
            Article.objects.filter(publications__id__exact=self.p1.id),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications__pk=self.p1.id),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications=self.p1.id),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications=self.p1),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications__title__startswith="Science"),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications__title__startswith="Science").distinct(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])

        # The count() function respects distinct() as well.
        self.assertEqual(Article.objects.filter(publications__title__startswith="Science").count(), 4)
        self.assertEqual(Article.objects.filter(publications__title__startswith="Science").distinct().count(), 3)
        self.assertQuerysetEqual(
            Article.objects.filter(publications__in=[self.p1.id,self.p2.id]).distinct(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications__in=[self.p1.id,self.p2]).distinct(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications__in=[self.p1,self.p2]).distinct(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])

        # Excluding a related item works as you would expect, too (although the SQL
        # involved is a little complex).
        self.assertQuerysetEqual(Article.objects.exclude(publications=self.p2),
                                 ['<Article: Django lets you build Web apps easily>'])

    def test_reverse_selects(self):
        # Reverse m2m queries are supported (i.e., starting at the table that
        # doesn't have a ManyToManyField).
        self.assertQuerysetEqual(Publication.objects.filter(id__exact=self.p1.id),
                                 ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(Publication.objects.filter(pk=self.p1.id),
                                 ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(
            Publication.objects.filter(article__headline__startswith="NASA"),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(Publication.objects.filter(article__id__exact=self.a1.id),
                                 ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(Publication.objects.filter(article__pk=self.a1.id),
                                 ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(Publication.objects.filter(article=self.a1.id),
                                 ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(Publication.objects.filter(article=self.a1),
                                 ['<Publication: The Python Journal>'])

        self.assertQuerysetEqual(
            Publication.objects.filter(article__in=[self.a1.id,self.a2.id]).distinct(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(
            Publication.objects.filter(article__in=[self.a1.id,self.a2]).distinct(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(
            Publication.objects.filter(article__in=[self.a1,self.a2]).distinct(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])

    def test_delete(self):
        # If we delete a Publication, its Articles won't be able to access it.
        self.p1.delete()
        self.assertQuerysetEqual(Publication.objects.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
            ])
        self.assertQuerysetEqual(self.a1.publications.all(), [])
        # If we delete an Article, its Publications won't be able to access it.
        self.a2.delete()
        self.assertQuerysetEqual(Article.objects.all(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ])

    def test_bulk_delete(self):
        # Bulk delete some Publications - references to deleted publications should go
        Publication.objects.filter(title__startswith='Science').delete()
        self.assertQuerysetEqual(Publication.objects.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(Article.objects.all(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(self.a2.publications.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: The Python Journal>',
            ])

        # Bulk delete some articles - references to deleted objects should go
        q = Article.objects.filter(headline__startswith='Django')
        self.assertQuerysetEqual(q, ['<Article: Django lets you build Web apps easily>'])
        q.delete()
        # After the delete, the QuerySet cache needs to be cleared,
        # and the referenced objects should be gone
        self.assertQuerysetEqual(q, [])
        self.assertQuerysetEqual(self.p1.article_set.all(),
                                 ['<Article: NASA uses Python>'])

    def test_remove(self):
        # Removing publication from an article:
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.a4.publications.remove(self.p2)
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(self.a4.publications.all(), [])
        # And from the other end
        self.p2.article_set.remove(self.a3)
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA uses Python>',
            ])
        self.assertQuerysetEqual(self.a3.publications.all(), [])

    def test_assign(self):
        # Relation sets can be assigned. Assignment clears any existing set members
        self.p2.article_set = [self.a4, self.a3]
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(self.a4.publications.all(),
                                 ['<Publication: Science News>'])
        self.a4.publications = [self.p3.id]
        self.assertQuerysetEqual(self.p2.article_set.all(),
                                 ['<Article: NASA finds intelligent life on Earth>'])
        self.assertQuerysetEqual(self.a4.publications.all(),
                                 ['<Publication: Science Weekly>'])

        # An alternate to calling clear() is to assign the empty set
        self.p2.article_set = []
        self.assertQuerysetEqual(self.p2.article_set.all(), [])
        self.a4.publications = []
        self.assertQuerysetEqual(self.a4.publications.all(), [])

    def test_assign_ids(self):
        # Relation sets can also be set using primary key values
        self.p2.article_set = [self.a4.id, self.a3.id]
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(self.a4.publications.all(),
                                 ['<Publication: Science News>'])
        self.a4.publications = [self.p3.id]
        self.assertQuerysetEqual(self.p2.article_set.all(),
                                 ['<Article: NASA finds intelligent life on Earth>'])
        self.assertQuerysetEqual(self.a4.publications.all(),
                                 ['<Publication: Science Weekly>'])

    def test_clear(self):
        # Relation sets can be cleared:
        self.p2.article_set.clear()
        self.assertQuerysetEqual(self.p2.article_set.all(), [])
        self.assertQuerysetEqual(self.a4.publications.all(), [])

        # And you can clear from the other end
        self.p2.article_set.add(self.a3, self.a4)
        self.assertQuerysetEqual(self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(self.a4.publications.all(),
            [
                '<Publication: Science News>',
            ])
        self.a4.publications.clear()
        self.assertQuerysetEqual(self.a4.publications.all(), [])
        self.assertQuerysetEqual(self.p2.article_set.all(),
                                 ['<Article: NASA finds intelligent life on Earth>'])

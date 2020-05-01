from unittest import mock

from django.db import transaction
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import (
    Article, InheritedArticleA, InheritedArticleB, Publication, User,
)


class ManyToManyTests(TestCase):

    def setUp(self):
        # Create a couple of Publications.
        self.p1 = Publication.objects.create(title='The Python Journal')
        self.p2 = Publication.objects.create(title='Science News')
        self.p3 = Publication.objects.create(title='Science Weekly')
        self.p4 = Publication.objects.create(title='Highlights for Children')

        self.a1 = Article.objects.create(headline='Django lets you build Web apps easily')
        self.a1.publications.add(self.p1)

        self.a2 = Article.objects.create(headline='NASA uses Python')
        self.a2.publications.add(self.p1, self.p2, self.p3, self.p4)

        self.a3 = Article.objects.create(headline='NASA finds intelligent life on Earth')
        self.a3.publications.add(self.p2)

        self.a4 = Article.objects.create(headline='Oxygen-free diet works wonders')
        self.a4.publications.add(self.p2)

    def test_add(self):
        # Create an Article.
        a5 = Article(headline='Django lets you create Web apps easily')
        # You can't associate it with a Publication until it's been saved.
        msg = (
            '"<Article: Django lets you create Web apps easily>" needs to have '
            'a value for field "id" before this many-to-many relationship can be used.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            getattr(a5, 'publications')
        # Save it!
        a5.save()
        # Associate the Article with a Publication.
        a5.publications.add(self.p1)
        self.assertQuerysetEqual(a5.publications.all(), ['<Publication: The Python Journal>'])
        # Create another Article, and set it to appear in both Publications.
        a6 = Article(headline='ESA uses Python')
        a6.save()
        a6.publications.add(self.p1, self.p2)
        a6.publications.add(self.p3)
        # Adding a second time is OK
        a6.publications.add(self.p3)
        self.assertQuerysetEqual(
            a6.publications.all(),
            [
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ]
        )

        # Adding an object of the wrong type raises TypeError
        msg = "'Publication' instance expected, got <Article: Django lets you create Web apps easily>"
        with self.assertRaisesMessage(TypeError, msg):
            with transaction.atomic():
                a6.publications.add(a5)

        # Add a Publication directly via publications.add by using keyword arguments.
        a6.publications.create(title='Highlights for Adults')
        self.assertQuerysetEqual(
            a6.publications.all(),
            [
                '<Publication: Highlights for Adults>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ]
        )

    def test_add_remove_set_by_pk(self):
        a5 = Article.objects.create(headline='Django lets you create Web apps easily')
        a5.publications.add(self.p1.pk)
        self.assertQuerysetEqual(
            a5.publications.all(),
            ['<Publication: The Python Journal>'],
        )
        a5.publications.set([self.p2.pk])
        self.assertQuerysetEqual(
            a5.publications.all(),
            ['<Publication: Science News>'],
        )
        a5.publications.remove(self.p2.pk)
        self.assertQuerysetEqual(a5.publications.all(), [])

    def test_add_remove_set_by_to_field(self):
        user_1 = User.objects.create(username='Jean')
        user_2 = User.objects.create(username='Joe')
        a5 = Article.objects.create(headline='Django lets you create Web apps easily')
        a5.authors.add(user_1.username)
        self.assertQuerysetEqual(a5.authors.all(), ['<User: Jean>'])
        a5.authors.set([user_2.username])
        self.assertQuerysetEqual(a5.authors.all(), ['<User: Joe>'])
        a5.authors.remove(user_2.username)
        self.assertQuerysetEqual(a5.authors.all(), [])

    def test_add_remove_invalid_type(self):
        msg = "Field 'id' expected a number but got 'invalid'."
        for method in ['add', 'remove']:
            with self.subTest(method), self.assertRaisesMessage(ValueError, msg):
                getattr(self.a1.publications, method)('invalid')

    def test_reverse_add(self):
        # Adding via the 'other' end of an m2m
        a5 = Article(headline='NASA finds intelligent life on Mars')
        a5.save()
        self.p2.article_set.add(a5)
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA finds intelligent life on Mars>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(a5.publications.all(), ['<Publication: Science News>'])

        # Adding via the other end using keywords
        self.p2.article_set.create(headline='Carbon-free diet works wonders')
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
        self.assertQuerysetEqual(
            a6.publications.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ]
        )

    @skipUnlessDBFeature('supports_ignore_conflicts')
    def test_fast_add_ignore_conflicts(self):
        """
        A single query is necessary to add auto-created through instances if
        the database backend supports bulk_create(ignore_conflicts) and no
        m2m_changed signals receivers are connected.
        """
        with self.assertNumQueries(1):
            self.a1.publications.add(self.p1, self.p2)

    @skipIfDBFeature('supports_ignore_conflicts')
    def test_add_existing_different_type(self):
        # A single SELECT query is necessary to compare existing values to the
        # provided one; no INSERT should be attempted.
        with self.assertNumQueries(1):
            self.a1.publications.add(str(self.p1.pk))
        self.assertEqual(self.a1.publications.get(), self.p1)

    @skipUnlessDBFeature('supports_ignore_conflicts')
    def test_slow_add_ignore_conflicts(self):
        manager_cls = self.a1.publications.__class__
        # Simulate a race condition between the missing ids retrieval and
        # the bulk insertion attempt.
        missing_target_ids = {self.p1.id}
        # Disable fast-add to test the case where the slow add path is taken.
        add_plan = (True, False, False)
        with mock.patch.object(manager_cls, '_get_missing_target_ids', return_value=missing_target_ids) as mocked:
            with mock.patch.object(manager_cls, '_get_add_plan', return_value=add_plan):
                self.a1.publications.add(self.p1)
        mocked.assert_called_once()

    def test_related_sets(self):
        # Article objects have access to their related Publication objects.
        self.assertQuerysetEqual(self.a1.publications.all(), ['<Publication: The Python Journal>'])
        self.assertQuerysetEqual(
            self.a2.publications.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ]
        )
        # Publication objects have access to their related Article objects.
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(
            self.p1.article_set.all(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ]
        )
        self.assertQuerysetEqual(
            Publication.objects.get(id=self.p4.id).article_set.all(),
            ['<Article: NASA uses Python>']
        )

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
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(publications=self.p1.id),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(publications=self.p1),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA uses Python>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(publications__title__startswith="Science"),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(publications__title__startswith="Science").distinct(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )

        # The count() function respects distinct() as well.
        self.assertEqual(Article.objects.filter(publications__title__startswith="Science").count(), 4)
        self.assertEqual(Article.objects.filter(publications__title__startswith="Science").distinct().count(), 3)
        self.assertQuerysetEqual(
            Article.objects.filter(publications__in=[self.p1.id, self.p2.id]).distinct(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(publications__in=[self.p1.id, self.p2]).distinct(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(publications__in=[self.p1, self.p2]).distinct(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )

        # Excluding a related item works as you would expect, too (although the SQL
        # involved is a little complex).
        self.assertQuerysetEqual(
            Article.objects.exclude(publications=self.p2),
            ['<Article: Django lets you build Web apps easily>']
        )

    def test_reverse_selects(self):
        # Reverse m2m queries are supported (i.e., starting at the table that
        # doesn't have a ManyToManyField).
        python_journal = ['<Publication: The Python Journal>']
        self.assertQuerysetEqual(Publication.objects.filter(id__exact=self.p1.id), python_journal)
        self.assertQuerysetEqual(Publication.objects.filter(pk=self.p1.id), python_journal)
        self.assertQuerysetEqual(
            Publication.objects.filter(article__headline__startswith="NASA"),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])

        self.assertQuerysetEqual(Publication.objects.filter(article__id__exact=self.a1.id), python_journal)
        self.assertQuerysetEqual(Publication.objects.filter(article__pk=self.a1.id), python_journal)
        self.assertQuerysetEqual(Publication.objects.filter(article=self.a1.id), python_journal)
        self.assertQuerysetEqual(Publication.objects.filter(article=self.a1), python_journal)

        self.assertQuerysetEqual(
            Publication.objects.filter(article__in=[self.a1.id, self.a2.id]).distinct(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(
            Publication.objects.filter(article__in=[self.a1.id, self.a2]).distinct(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(
            Publication.objects.filter(article__in=[self.a1, self.a2]).distinct(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
                '<Publication: The Python Journal>',
            ])

    def test_delete(self):
        # If we delete a Publication, its Articles won't be able to access it.
        self.p1.delete()
        self.assertQuerysetEqual(
            Publication.objects.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: Science News>',
                '<Publication: Science Weekly>',
            ]
        )
        self.assertQuerysetEqual(self.a1.publications.all(), [])
        # If we delete an Article, its Publications won't be able to access it.
        self.a2.delete()
        self.assertQuerysetEqual(
            Article.objects.all(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )

    def test_bulk_delete(self):
        # Bulk delete some Publications - references to deleted publications should go
        Publication.objects.filter(title__startswith='Science').delete()
        self.assertQuerysetEqual(
            Publication.objects.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: The Python Journal>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.all(),
            [
                '<Article: Django lets you build Web apps easily>',
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(
            self.a2.publications.all(),
            [
                '<Publication: Highlights for Children>',
                '<Publication: The Python Journal>',
            ]
        )

        # Bulk delete some articles - references to deleted objects should go
        q = Article.objects.filter(headline__startswith='Django')
        self.assertQuerysetEqual(q, ['<Article: Django lets you build Web apps easily>'])
        q.delete()
        # After the delete, the QuerySet cache needs to be cleared,
        # and the referenced objects should be gone
        self.assertQuerysetEqual(q, [])
        self.assertQuerysetEqual(self.p1.article_set.all(), ['<Article: NASA uses Python>'])

    def test_remove(self):
        # Removing publication from an article:
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.a4.publications.remove(self.p2)
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: NASA uses Python>',
            ]
        )
        self.assertQuerysetEqual(self.a4.publications.all(), [])
        # And from the other end
        self.p2.article_set.remove(self.a3)
        self.assertQuerysetEqual(self.p2.article_set.all(), ['<Article: NASA uses Python>'])
        self.assertQuerysetEqual(self.a3.publications.all(), [])

    def test_set(self):
        self.p2.article_set.set([self.a4, self.a3])
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science News>'])
        self.a4.publications.set([self.p3.id])
        self.assertQuerysetEqual(self.p2.article_set.all(), ['<Article: NASA finds intelligent life on Earth>'])
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science Weekly>'])

        self.p2.article_set.set([])
        self.assertQuerysetEqual(self.p2.article_set.all(), [])
        self.a4.publications.set([])
        self.assertQuerysetEqual(self.a4.publications.all(), [])

        self.p2.article_set.set([self.a4, self.a3], clear=True)
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science News>'])
        self.a4.publications.set([self.p3.id], clear=True)
        self.assertQuerysetEqual(self.p2.article_set.all(), ['<Article: NASA finds intelligent life on Earth>'])
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science Weekly>'])

        self.p2.article_set.set([], clear=True)
        self.assertQuerysetEqual(self.p2.article_set.all(), [])
        self.a4.publications.set([], clear=True)
        self.assertQuerysetEqual(self.a4.publications.all(), [])

    def test_set_existing_different_type(self):
        # Existing many-to-many relations remain the same for values provided
        # with a different type.
        ids = set(Publication.article_set.through.objects.filter(
            article__in=[self.a4, self.a3],
            publication=self.p2,
        ).values_list('id', flat=True))
        self.p2.article_set.set([str(self.a4.pk), str(self.a3.pk)])
        new_ids = set(Publication.article_set.through.objects.filter(
            publication=self.p2,
        ).values_list('id', flat=True))
        self.assertEqual(ids, new_ids)

    def test_assign_forward(self):
        msg = (
            "Direct assignment to the reverse side of a many-to-many set is "
            "prohibited. Use article_set.set() instead."
        )
        with self.assertRaisesMessage(TypeError, msg):
            self.p2.article_set = [self.a4, self.a3]

    def test_assign_reverse(self):
        msg = (
            "Direct assignment to the forward side of a many-to-many "
            "set is prohibited. Use publications.set() instead."
        )
        with self.assertRaisesMessage(TypeError, msg):
            self.a1.publications = [self.p1, self.p2]

    def test_assign(self):
        # Relation sets can be assigned using set().
        self.p2.article_set.set([self.a4, self.a3])
        self.assertQuerysetEqual(
            self.p2.article_set.all(), [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science News>'])
        self.a4.publications.set([self.p3.id])
        self.assertQuerysetEqual(self.p2.article_set.all(), ['<Article: NASA finds intelligent life on Earth>'])
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science Weekly>'])

        # An alternate to calling clear() is to set an empty set.
        self.p2.article_set.set([])
        self.assertQuerysetEqual(self.p2.article_set.all(), [])
        self.a4.publications.set([])
        self.assertQuerysetEqual(self.a4.publications.all(), [])

    def test_assign_ids(self):
        # Relation sets can also be set using primary key values
        self.p2.article_set.set([self.a4.id, self.a3.id])
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science News>'])
        self.a4.publications.set([self.p3.id])
        self.assertQuerysetEqual(self.p2.article_set.all(), ['<Article: NASA finds intelligent life on Earth>'])
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science Weekly>'])

    def test_forward_assign_with_queryset(self):
        # Querysets used in m2m assignments are pre-evaluated so their value
        # isn't affected by the clearing operation in ManyRelatedManager.set()
        # (#19816).
        self.a1.publications.set([self.p1, self.p2])

        qs = self.a1.publications.filter(title='The Python Journal')
        self.a1.publications.set(qs)

        self.assertEqual(1, self.a1.publications.count())
        self.assertEqual(1, qs.count())

    def test_reverse_assign_with_queryset(self):
        # Querysets used in M2M assignments are pre-evaluated so their value
        # isn't affected by the clearing operation in ManyRelatedManager.set()
        # (#19816).
        self.p1.article_set.set([self.a1, self.a2])

        qs = self.p1.article_set.filter(headline='Django lets you build Web apps easily')
        self.p1.article_set.set(qs)

        self.assertEqual(1, self.p1.article_set.count())
        self.assertEqual(1, qs.count())

    def test_clear(self):
        # Relation sets can be cleared:
        self.p2.article_set.clear()
        self.assertQuerysetEqual(self.p2.article_set.all(), [])
        self.assertQuerysetEqual(self.a4.publications.all(), [])

        # And you can clear from the other end
        self.p2.article_set.add(self.a3, self.a4)
        self.assertQuerysetEqual(
            self.p2.article_set.all(),
            [
                '<Article: NASA finds intelligent life on Earth>',
                '<Article: Oxygen-free diet works wonders>',
            ]
        )
        self.assertQuerysetEqual(self.a4.publications.all(), ['<Publication: Science News>'])
        self.a4.publications.clear()
        self.assertQuerysetEqual(self.a4.publications.all(), [])
        self.assertQuerysetEqual(self.p2.article_set.all(), ['<Article: NASA finds intelligent life on Earth>'])

    def test_clear_after_prefetch(self):
        a4 = Article.objects.prefetch_related('publications').get(id=self.a4.id)
        self.assertQuerysetEqual(a4.publications.all(), ['<Publication: Science News>'])
        a4.publications.clear()
        self.assertQuerysetEqual(a4.publications.all(), [])

    def test_remove_after_prefetch(self):
        a4 = Article.objects.prefetch_related('publications').get(id=self.a4.id)
        self.assertQuerysetEqual(a4.publications.all(), ['<Publication: Science News>'])
        a4.publications.remove(self.p2)
        self.assertQuerysetEqual(a4.publications.all(), [])

    def test_add_after_prefetch(self):
        a4 = Article.objects.prefetch_related('publications').get(id=self.a4.id)
        self.assertEqual(a4.publications.count(), 1)
        a4.publications.add(self.p1)
        self.assertEqual(a4.publications.count(), 2)

    def test_set_after_prefetch(self):
        a4 = Article.objects.prefetch_related('publications').get(id=self.a4.id)
        self.assertEqual(a4.publications.count(), 1)
        a4.publications.set([self.p2, self.p1])
        self.assertEqual(a4.publications.count(), 2)
        a4.publications.set([self.p1])
        self.assertEqual(a4.publications.count(), 1)

    def test_add_then_remove_after_prefetch(self):
        a4 = Article.objects.prefetch_related('publications').get(id=self.a4.id)
        self.assertEqual(a4.publications.count(), 1)
        a4.publications.add(self.p1)
        self.assertEqual(a4.publications.count(), 2)
        a4.publications.remove(self.p1)
        self.assertQuerysetEqual(a4.publications.all(), ['<Publication: Science News>'])

    def test_inherited_models_selects(self):
        """
        #24156 - Objects from child models where the parent's m2m field uses
        related_name='+' should be retrieved correctly.
        """
        a = InheritedArticleA.objects.create()
        b = InheritedArticleB.objects.create()
        a.publications.add(self.p1, self.p2)
        self.assertQuerysetEqual(
            a.publications.all(),
            [
                '<Publication: Science News>',
                '<Publication: The Python Journal>',
            ])
        self.assertQuerysetEqual(b.publications.all(), [])
        b.publications.add(self.p3)
        self.assertQuerysetEqual(
            a.publications.all(),
            [
                '<Publication: Science News>',
                '<Publication: The Python Journal>',
            ]
        )
        self.assertQuerysetEqual(b.publications.all(), ['<Publication: Science Weekly>'])

    def test_custom_default_manager_exists_count(self):
        a5 = Article.objects.create(headline='deleted')
        a5.publications.add(self.p2)
        self.assertEqual(self.p2.article_set.count(), self.p2.article_set.all().count())
        self.assertEqual(self.p3.article_set.exists(), self.p3.article_set.all().exists())

from unittest import mock

from django.db import connection, transaction
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from .models import (
    Article,
    CustomArticle,
    InheritedArticleA,
    InheritedArticleB,
    NullablePublicationThrough,
    NullableTargetArticle,
    Publication,
    User,
)


class ManyToManyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a couple of Publications.
        cls.p1 = Publication.objects.create(title="The Python Journal")
        cls.p2 = Publication.objects.create(title="Science News")
        cls.p3 = Publication.objects.create(title="Science Weekly")
        cls.p4 = Publication.objects.create(title="Highlights for Children")

        cls.a1 = Article.objects.create(
            headline="Django lets you build web apps easily"
        )
        cls.a1.publications.add(cls.p1)

        cls.a2 = Article.objects.create(headline="NASA uses Python")
        cls.a2.publications.add(cls.p1, cls.p2, cls.p3, cls.p4)

        cls.a3 = Article.objects.create(headline="NASA finds intelligent life on Earth")
        cls.a3.publications.add(cls.p2)

        cls.a4 = Article.objects.create(headline="Oxygen-free diet works wonders")
        cls.a4.publications.add(cls.p2)

    def test_add(self):
        # Create an Article.
        a5 = Article(headline="Django lets you create web apps easily")
        # You can't associate it with a Publication until it's been saved.
        msg = (
            '"<Article: Django lets you create web apps easily>" needs to have '
            'a value for field "id" before this many-to-many relationship can be used.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            getattr(a5, "publications")
        # Save it!
        a5.save()
        # Associate the Article with a Publication.
        a5.publications.add(self.p1)
        self.assertSequenceEqual(a5.publications.all(), [self.p1])
        # Create another Article, and set it to appear in both Publications.
        a6 = Article(headline="ESA uses Python")
        a6.save()
        a6.publications.add(self.p1, self.p2)
        a6.publications.add(self.p3)
        # Adding a second time is OK
        a6.publications.add(self.p3)
        self.assertSequenceEqual(
            a6.publications.all(),
            [self.p2, self.p3, self.p1],
        )

        # Adding an object of the wrong type raises TypeError
        msg = (
            "'Publication' instance expected, got <Article: Django lets you create web "
            "apps easily>"
        )
        with self.assertRaisesMessage(TypeError, msg):
            with transaction.atomic():
                a6.publications.add(a5)

        # Add a Publication directly via publications.add by using keyword arguments.
        p5 = a6.publications.create(title="Highlights for Adults")
        self.assertSequenceEqual(
            a6.publications.all(),
            [p5, self.p2, self.p3, self.p1],
        )

    def test_add_remove_set_by_pk(self):
        a5 = Article.objects.create(headline="Django lets you create web apps easily")
        a5.publications.add(self.p1.pk)
        self.assertSequenceEqual(a5.publications.all(), [self.p1])
        a5.publications.set([self.p2.pk])
        self.assertSequenceEqual(a5.publications.all(), [self.p2])
        a5.publications.remove(self.p2.pk)
        self.assertSequenceEqual(a5.publications.all(), [])

    def test_add_remove_set_by_to_field(self):
        user_1 = User.objects.create(username="Jean")
        user_2 = User.objects.create(username="Joe")
        a5 = Article.objects.create(headline="Django lets you create web apps easily")
        a5.authors.add(user_1.username)
        self.assertSequenceEqual(a5.authors.all(), [user_1])
        a5.authors.set([user_2.username])
        self.assertSequenceEqual(a5.authors.all(), [user_2])
        a5.authors.remove(user_2.username)
        self.assertSequenceEqual(a5.authors.all(), [])

    def test_related_manager_refresh(self):
        user_1 = User.objects.create(username="Jean")
        user_2 = User.objects.create(username="Joe")
        self.a3.authors.add(user_1.username)
        self.assertSequenceEqual(user_1.article_set.all(), [self.a3])
        # Change the username on a different instance of the same user.
        user_1_from_db = User.objects.get(pk=user_1.pk)
        self.assertSequenceEqual(user_1_from_db.article_set.all(), [self.a3])
        user_1_from_db.username = "Paul"
        self.a3.authors.set([user_2.username])
        user_1_from_db.save()
        # Assign a different article.
        self.a4.authors.add(user_1_from_db.username)
        self.assertSequenceEqual(user_1_from_db.article_set.all(), [self.a4])
        # Refresh the instance with an evaluated related manager.
        user_1.refresh_from_db()
        self.assertEqual(user_1.username, "Paul")
        self.assertSequenceEqual(user_1.article_set.all(), [self.a4])

    def test_add_remove_invalid_type(self):
        msg = "Field 'id' expected a number but got 'invalid'."
        for method in ["add", "remove"]:
            with self.subTest(method), self.assertRaisesMessage(ValueError, msg):
                getattr(self.a1.publications, method)("invalid")

    def test_reverse_add(self):
        # Adding via the 'other' end of an m2m
        a5 = Article(headline="NASA finds intelligent life on Mars")
        a5.save()
        self.p2.article_set.add(a5)
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, a5, self.a2, self.a4],
        )
        self.assertSequenceEqual(a5.publications.all(), [self.p2])

        # Adding via the other end using keywords
        a6 = self.p2.article_set.create(headline="Carbon-free diet works wonders")
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [a6, self.a3, a5, self.a2, self.a4],
        )
        a6 = self.p2.article_set.all()[3]
        self.assertSequenceEqual(
            a6.publications.all(),
            [self.p4, self.p2, self.p3, self.p1],
        )

    @skipUnlessDBFeature("supports_ignore_conflicts")
    def test_fast_add_ignore_conflicts(self):
        """
        A single query is necessary to add auto-created through instances if
        the database backend supports bulk_create(ignore_conflicts) and no
        m2m_changed signals receivers are connected.
        """
        with self.assertNumQueries(1):
            self.a1.publications.add(self.p1, self.p2)

    @skipIfDBFeature("supports_ignore_conflicts")
    def test_add_existing_different_type(self):
        # A single SELECT query is necessary to compare existing values to the
        # provided one; no INSERT should be attempted.
        with self.assertNumQueries(1):
            self.a1.publications.add(str(self.p1.pk))
        self.assertEqual(self.a1.publications.get(), self.p1)

    @skipUnlessDBFeature("supports_ignore_conflicts")
    def test_slow_add_ignore_conflicts(self):
        manager_cls = self.a1.publications.__class__
        # Simulate a race condition between the missing ids retrieval and
        # the bulk insertion attempt.
        missing_target_ids = {self.p1.id}
        # Disable fast-add to test the case where the slow add path is taken.
        add_plan = (True, False, False)
        with mock.patch.object(
            manager_cls, "_get_missing_target_ids", return_value=missing_target_ids
        ) as mocked:
            with mock.patch.object(manager_cls, "_get_add_plan", return_value=add_plan):
                self.a1.publications.add(self.p1)
        mocked.assert_called_once()

    def test_related_sets(self):
        # Article objects have access to their related Publication objects.
        self.assertSequenceEqual(self.a1.publications.all(), [self.p1])
        self.assertSequenceEqual(
            self.a2.publications.all(),
            [self.p4, self.p2, self.p3, self.p1],
        )
        # Publication objects have access to their related Article objects.
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a2, self.a4],
        )
        self.assertSequenceEqual(
            self.p1.article_set.all(),
            [self.a1, self.a2],
        )
        self.assertSequenceEqual(
            Publication.objects.get(id=self.p4.id).article_set.all(),
            [self.a2],
        )

    def test_selects(self):
        # We can perform kwarg queries across m2m relationships
        self.assertSequenceEqual(
            Article.objects.filter(publications__id__exact=self.p1.id),
            [self.a1, self.a2],
        )
        self.assertSequenceEqual(
            Article.objects.filter(publications__pk=self.p1.id),
            [self.a1, self.a2],
        )
        self.assertSequenceEqual(
            Article.objects.filter(publications=self.p1.id),
            [self.a1, self.a2],
        )
        self.assertSequenceEqual(
            Article.objects.filter(publications=self.p1),
            [self.a1, self.a2],
        )
        self.assertSequenceEqual(
            Article.objects.filter(publications__title__startswith="Science"),
            [self.a3, self.a2, self.a2, self.a4],
        )
        self.assertSequenceEqual(
            Article.objects.filter(
                publications__title__startswith="Science"
            ).distinct(),
            [self.a3, self.a2, self.a4],
        )

        # The count() function respects distinct() as well.
        self.assertEqual(
            Article.objects.filter(publications__title__startswith="Science").count(), 4
        )
        self.assertEqual(
            Article.objects.filter(publications__title__startswith="Science")
            .distinct()
            .count(),
            3,
        )
        self.assertSequenceEqual(
            Article.objects.filter(
                publications__in=[self.p1.id, self.p2.id]
            ).distinct(),
            [self.a1, self.a3, self.a2, self.a4],
        )
        self.assertSequenceEqual(
            Article.objects.filter(publications__in=[self.p1.id, self.p2]).distinct(),
            [self.a1, self.a3, self.a2, self.a4],
        )
        self.assertSequenceEqual(
            Article.objects.filter(publications__in=[self.p1, self.p2]).distinct(),
            [self.a1, self.a3, self.a2, self.a4],
        )

        # Excluding a related item works as you would expect, too (although the SQL
        # involved is a little complex).
        self.assertSequenceEqual(
            Article.objects.exclude(publications=self.p2),
            [self.a1],
        )

    def test_reverse_selects(self):
        # Reverse m2m queries are supported (i.e., starting at the table that
        # doesn't have a ManyToManyField).
        python_journal = [self.p1]
        self.assertSequenceEqual(
            Publication.objects.filter(id__exact=self.p1.id), python_journal
        )
        self.assertSequenceEqual(
            Publication.objects.filter(pk=self.p1.id), python_journal
        )
        self.assertSequenceEqual(
            Publication.objects.filter(article__headline__startswith="NASA"),
            [self.p4, self.p2, self.p2, self.p3, self.p1],
        )

        self.assertSequenceEqual(
            Publication.objects.filter(article__id__exact=self.a1.id), python_journal
        )
        self.assertSequenceEqual(
            Publication.objects.filter(article__pk=self.a1.id), python_journal
        )
        self.assertSequenceEqual(
            Publication.objects.filter(article=self.a1.id), python_journal
        )
        self.assertSequenceEqual(
            Publication.objects.filter(article=self.a1), python_journal
        )

        self.assertSequenceEqual(
            Publication.objects.filter(article__in=[self.a1.id, self.a2.id]).distinct(),
            [self.p4, self.p2, self.p3, self.p1],
        )
        self.assertSequenceEqual(
            Publication.objects.filter(article__in=[self.a1.id, self.a2]).distinct(),
            [self.p4, self.p2, self.p3, self.p1],
        )
        self.assertSequenceEqual(
            Publication.objects.filter(article__in=[self.a1, self.a2]).distinct(),
            [self.p4, self.p2, self.p3, self.p1],
        )

    def test_delete(self):
        # If we delete a Publication, its Articles won't be able to access it.
        self.p1.delete()
        self.assertSequenceEqual(
            Publication.objects.all(),
            [self.p4, self.p2, self.p3],
        )
        self.assertSequenceEqual(self.a1.publications.all(), [])
        # If we delete an Article, its Publications won't be able to access it.
        self.a2.delete()
        self.assertSequenceEqual(
            Article.objects.all(),
            [self.a1, self.a3, self.a4],
        )
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a4],
        )

    def test_bulk_delete(self):
        # Bulk delete some Publications - references to deleted publications should go
        Publication.objects.filter(title__startswith="Science").delete()
        self.assertSequenceEqual(
            Publication.objects.all(),
            [self.p4, self.p1],
        )
        self.assertSequenceEqual(
            Article.objects.all(),
            [self.a1, self.a3, self.a2, self.a4],
        )
        self.assertSequenceEqual(
            self.a2.publications.all(),
            [self.p4, self.p1],
        )

        # Bulk delete some articles - references to deleted objects should go
        q = Article.objects.filter(headline__startswith="Django")
        self.assertSequenceEqual(q, [self.a1])
        q.delete()
        # After the delete, the QuerySet cache needs to be cleared,
        # and the referenced objects should be gone
        self.assertSequenceEqual(q, [])
        self.assertSequenceEqual(self.p1.article_set.all(), [self.a2])

    def test_remove(self):
        # Removing publication from an article:
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a2, self.a4],
        )
        self.a4.publications.remove(self.p2)
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a2],
        )
        self.assertSequenceEqual(self.a4.publications.all(), [])
        # And from the other end
        self.p2.article_set.remove(self.a3)
        self.assertSequenceEqual(self.p2.article_set.all(), [self.a2])
        self.assertSequenceEqual(self.a3.publications.all(), [])

    def test_set(self):
        self.p2.article_set.set([self.a4, self.a3])
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a4],
        )
        self.assertSequenceEqual(self.a4.publications.all(), [self.p2])
        self.a4.publications.set([self.p3.id])
        self.assertSequenceEqual(self.p2.article_set.all(), [self.a3])
        self.assertSequenceEqual(self.a4.publications.all(), [self.p3])

        self.p2.article_set.set([])
        self.assertSequenceEqual(self.p2.article_set.all(), [])
        self.a4.publications.set([])
        self.assertSequenceEqual(self.a4.publications.all(), [])

        self.p2.article_set.set([self.a4, self.a3], clear=True)
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a4],
        )
        self.assertSequenceEqual(self.a4.publications.all(), [self.p2])
        self.a4.publications.set([self.p3.id], clear=True)
        self.assertSequenceEqual(self.p2.article_set.all(), [self.a3])
        self.assertSequenceEqual(self.a4.publications.all(), [self.p3])

        self.p2.article_set.set([], clear=True)
        self.assertSequenceEqual(self.p2.article_set.all(), [])
        self.a4.publications.set([], clear=True)
        self.assertSequenceEqual(self.a4.publications.all(), [])

    def test_set_existing_different_type(self):
        # Existing many-to-many relations remain the same for values provided
        # with a different type.
        ids = set(
            Publication.article_set.through.objects.filter(
                article__in=[self.a4, self.a3],
                publication=self.p2,
            ).values_list("id", flat=True)
        )
        self.p2.article_set.set([str(self.a4.pk), str(self.a3.pk)])
        new_ids = set(
            Publication.article_set.through.objects.filter(
                publication=self.p2,
            ).values_list("id", flat=True)
        )
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
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a4],
        )
        self.assertSequenceEqual(self.a4.publications.all(), [self.p2])
        self.a4.publications.set([self.p3.id])
        self.assertSequenceEqual(self.p2.article_set.all(), [self.a3])
        self.assertSequenceEqual(self.a4.publications.all(), [self.p3])

        # An alternate to calling clear() is to set an empty set.
        self.p2.article_set.set([])
        self.assertSequenceEqual(self.p2.article_set.all(), [])
        self.a4.publications.set([])
        self.assertSequenceEqual(self.a4.publications.all(), [])

    def test_assign_ids(self):
        # Relation sets can also be set using primary key values
        self.p2.article_set.set([self.a4.id, self.a3.id])
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a4],
        )
        self.assertSequenceEqual(self.a4.publications.all(), [self.p2])
        self.a4.publications.set([self.p3.id])
        self.assertSequenceEqual(self.p2.article_set.all(), [self.a3])
        self.assertSequenceEqual(self.a4.publications.all(), [self.p3])

    def test_forward_assign_with_queryset(self):
        # Querysets used in m2m assignments are pre-evaluated so their value
        # isn't affected by the clearing operation in ManyRelatedManager.set()
        # (#19816).
        self.a1.publications.set([self.p1, self.p2])

        qs = self.a1.publications.filter(title="The Python Journal")
        self.a1.publications.set(qs)

        self.assertEqual(1, self.a1.publications.count())
        self.assertEqual(1, qs.count())

    def test_reverse_assign_with_queryset(self):
        # Querysets used in M2M assignments are pre-evaluated so their value
        # isn't affected by the clearing operation in ManyRelatedManager.set()
        # (#19816).
        self.p1.article_set.set([self.a1, self.a2])

        qs = self.p1.article_set.filter(
            headline="Django lets you build web apps easily"
        )
        self.p1.article_set.set(qs)

        self.assertEqual(1, self.p1.article_set.count())
        self.assertEqual(1, qs.count())

    def test_clear(self):
        # Relation sets can be cleared:
        self.p2.article_set.clear()
        self.assertSequenceEqual(self.p2.article_set.all(), [])
        self.assertSequenceEqual(self.a4.publications.all(), [])

        # And you can clear from the other end
        self.p2.article_set.add(self.a3, self.a4)
        self.assertSequenceEqual(
            self.p2.article_set.all(),
            [self.a3, self.a4],
        )
        self.assertSequenceEqual(self.a4.publications.all(), [self.p2])
        self.a4.publications.clear()
        self.assertSequenceEqual(self.a4.publications.all(), [])
        self.assertSequenceEqual(self.p2.article_set.all(), [self.a3])

    def test_clear_after_prefetch(self):
        a4 = Article.objects.prefetch_related("publications").get(id=self.a4.id)
        self.assertSequenceEqual(a4.publications.all(), [self.p2])
        a4.publications.clear()
        self.assertSequenceEqual(a4.publications.all(), [])

    def test_remove_after_prefetch(self):
        a4 = Article.objects.prefetch_related("publications").get(id=self.a4.id)
        self.assertSequenceEqual(a4.publications.all(), [self.p2])
        a4.publications.remove(self.p2)
        self.assertSequenceEqual(a4.publications.all(), [])

    def test_add_after_prefetch(self):
        a4 = Article.objects.prefetch_related("publications").get(id=self.a4.id)
        self.assertEqual(a4.publications.count(), 1)
        a4.publications.add(self.p1)
        self.assertEqual(a4.publications.count(), 2)

    def test_set_after_prefetch(self):
        a4 = Article.objects.prefetch_related("publications").get(id=self.a4.id)
        self.assertEqual(a4.publications.count(), 1)
        a4.publications.set([self.p2, self.p1])
        self.assertEqual(a4.publications.count(), 2)
        a4.publications.set([self.p1])
        self.assertEqual(a4.publications.count(), 1)

    def test_add_then_remove_after_prefetch(self):
        a4 = Article.objects.prefetch_related("publications").get(id=self.a4.id)
        self.assertEqual(a4.publications.count(), 1)
        a4.publications.add(self.p1)
        self.assertEqual(a4.publications.count(), 2)
        a4.publications.remove(self.p1)
        self.assertSequenceEqual(a4.publications.all(), [self.p2])

    def test_inherited_models_selects(self):
        """
        #24156 - Objects from child models where the parent's m2m field uses
        related_name='+' should be retrieved correctly.
        """
        a = InheritedArticleA.objects.create()
        b = InheritedArticleB.objects.create()
        a.publications.add(self.p1, self.p2)
        self.assertSequenceEqual(
            a.publications.all(),
            [self.p2, self.p1],
        )
        self.assertSequenceEqual(b.publications.all(), [])
        b.publications.add(self.p3)
        self.assertSequenceEqual(
            a.publications.all(),
            [self.p2, self.p1],
        )
        self.assertSequenceEqual(b.publications.all(), [self.p3])

    def test_custom_default_manager_exists_count(self):
        a5 = Article.objects.create(headline="deleted")
        a5.publications.add(self.p2)
        self.assertEqual(self.p2.article_set.count(), self.p2.article_set.all().count())
        self.assertEqual(
            self.p3.article_set.exists(), self.p3.article_set.all().exists()
        )


class ManyToManyQueryTests(TestCase):
    """
      #29725 - Testing SQL optimization when using
      count() and exists() functions on queryset for
      many to many relations
    """
    @classmethod
    def setUpTestData(cls):
        cls.article = Article.objects.create(
            headline='Django lets you build Web apps easily'
        )
        cls.nullable_target_article = (
            NullableTargetArticle.objects.create(
                headline='The python is good'
            )
        )
        NullablePublicationThrough.objects.create(
            article=cls.nullable_target_article, publication=None
        )
        cls.custom_article = CustomArticle.objects.create(
            headline='Django lets you build Web apps easily'
        )

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_count_join_optimization(self):
        with self.assertNumQueries(1) as queries:
            self.article.publications.count()

        self.assertNotIn('JOIN', queries[0]['sql'])
        self.article.publications.prefetch_related()
        with self.assertNumQueries(1) as queries:
            self.article.publications.count()

        self.assertNotIn('JOIN', queries[0]['sql'])
        self.assertEqual(self.nullable_target_article.publications.count(), 0)

    def test_count_join_optimization_disabled(self):
        with mock.patch.object(connection.features, 'supports_foreign_keys', False), \
                CaptureQueriesContext(connection) as query:
            self.article.publications.count()
            self.custom_article.publications.count()

        self.assertIn('JOIN', query[0]['sql'])

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_exists_join_optimization(self):
        with CaptureQueriesContext(connection) as query:
            self.article.publications.exists()

        self.assertNotIn('JOIN', query[0]['sql'])
        self.article.publications.prefetch_related()
        with self.assertNumQueries(1):
            self.article.publications.exists()

        self.assertNotIn('JOIN', query[0]['sql'])
        self.assertIs(self.nullable_target_article.publications.exists(), False)

    def test_exists_join_optimization_disabled(self):
        with mock.patch.object(connection.features, 'supports_foreign_keys', False), \
                CaptureQueriesContext(connection) as query:
            self.article.publications.exists()
            self.custom_article.publications.exists()

        self.assertIn('JOIN', query[0]['sql'])

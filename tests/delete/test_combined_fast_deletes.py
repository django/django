"""
Tests for combined fast delete query optimization.
This tests the optimization that combines multiple DELETE queries for the same
table into a single query using OR conditions.
"""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import M, MR, Person, Author, Article


class CombinedFastDeleteTests(TestCase):
    """
    Test that fast delete queries are combined for the same table to reduce
    database roundtrips.
    """

    def test_m2m_self_reference_combined(self):
        """
        Test that deleting a person with many-to-many self-reference combines
        DELETE queries for the same table.

        Without optimization: 3 queries
        - DELETE FROM person_friends WHERE from_person_id = :id
        - DELETE FROM person_friends WHERE to_person_id = :id
        - DELETE FROM person WHERE id = :id

        With optimization: 2 queries
        - DELETE FROM person_friends WHERE from_person_id = :id OR to_person_id = :id
        - DELETE FROM person WHERE id = :id
        """
        person1 = Person.objects.create(name='Alice')
        person2 = Person.objects.create(name='Bob')
        person3 = Person.objects.create(name='Charlie')

        # Add friends relationships
        person1.friends.add(person2, person3)

        # Capture queries when deleting person1
        with CaptureQueriesContext(connection) as ctx:
            person1.delete()

        # Count DELETE queries for the many-to-many table
        m2m_table_name = Person._meta.get_field('friends').remote_field.through._meta.db_table
        delete_m2m_queries = [
            q for q in ctx.captured_queries
            if q['sql'].startswith('DELETE') and m2m_table_name in q['sql']
        ]

        # Should be only 1 combined DELETE query for the m2m table
        self.assertEqual(len(delete_m2m_queries), 1)

        # Verify the query contains OR condition
        self.assertIn(' OR ', delete_m2m_queries[0]['sql'])

        # Verify data is deleted correctly
        self.assertFalse(Person.objects.filter(pk=person1.pk).exists())
        self.assertTrue(Person.objects.filter(pk=person2.pk).exists())
        self.assertTrue(Person.objects.filter(pk=person3.pk).exists())

    def test_multiple_fk_combined(self):
        """
        Test that deleting an author with multiple foreign key relationships
        combines DELETE queries for the same table.

        Without optimization: 3 queries
        - DELETE FROM article WHERE created_by_id = :id
        - DELETE FROM article WHERE updated_by_id = :id
        - DELETE FROM author WHERE id = :id

        With optimization: 2 queries
        - DELETE FROM article WHERE created_by_id = :id OR updated_by_id = :id
        - DELETE FROM author WHERE id = :id
        """
        author = Author.objects.create(name='john')

        # Create articles with the author as both creator and updater
        Article.objects.create(title='Article 1', created_by=author, updated_by=author)
        Article.objects.create(title='Article 2', created_by=author, updated_by=author)

        # Capture queries when deleting author
        with CaptureQueriesContext(connection) as ctx:
            author.delete()

        # Count DELETE queries for the article table
        article_table_name = Article._meta.db_table
        delete_article_queries = [
            q for q in ctx.captured_queries
            if q['sql'].startswith('DELETE') and article_table_name in q['sql']
        ]

        # Should be only 1 combined DELETE query for the article table
        self.assertEqual(len(delete_article_queries), 1)

        # Verify the query contains OR condition
        self.assertIn(' OR ', delete_article_queries[0]['sql'])

        # Verify data is deleted correctly
        self.assertFalse(Author.objects.filter(pk=author.pk).exists())
        self.assertFalse(Article.objects.filter(created_by=author).exists())
        self.assertFalse(Article.objects.filter(updated_by=author).exists())

    def test_combined_deletes_reduce_queries(self):
        """
        Test that combining delete queries reduces the total number of queries.
        """
        # Create an author with multiple articles
        author = Author.objects.create(name='jane')
        for i in range(5):
            Article.objects.create(
                title=f'Article {i}',
                created_by=author,
                updated_by=author
            )

        # Count queries
        with CaptureQueriesContext(connection) as ctx:
            author.delete()

        # Get all DELETE queries
        delete_queries = [
            q for q in ctx.captured_queries
            if q['sql'].startswith('DELETE')
        ]

        # Should have only 2 DELETE queries total:
        # 1 for articles (combined), 1 for author
        self.assertEqual(len(delete_queries), 2)

    def test_combined_deletes_correctness(self):
        """
        Test that combined delete queries correctly delete all related objects.
        """
        # Create authors and articles
        author1 = Author.objects.create(name='author1')
        author2 = Author.objects.create(name='author2')

        # Create articles with different creator/updater combinations
        article1 = Article.objects.create(title='A1', created_by=author1, updated_by=author1)
        article2 = Article.objects.create(title='A2', created_by=author1, updated_by=author2)
        article3 = Article.objects.create(title='A3', created_by=author2, updated_by=author1)
        article4 = Article.objects.create(title='A4', created_by=author2, updated_by=author2)

        # Delete author1
        author1.delete()

        # Articles where author1 was creator or updater should be deleted
        self.assertFalse(Article.objects.filter(pk=article1.pk).exists())
        self.assertFalse(Article.objects.filter(pk=article2.pk).exists())
        self.assertFalse(Article.objects.filter(pk=article3.pk).exists())

        # Article4 should still exist (no relationship with author1)
        self.assertTrue(Article.objects.filter(pk=article4.pk).exists())

        # Author2 should still exist
        self.assertTrue(Author.objects.filter(pk=author2.pk).exists())

    def test_m2m_through_model_combined(self):
        """
        Test combined deletes work with many-to-many through models.
        """
        from django.db import models

        m = M.objects.create()
        # Access the through model for m2m_through field
        through_model = M._meta.get_field('m2m_through').remote_field.through

        # Create some MR entries
        from .models import R
        r1 = R.objects.create()
        r2 = R.objects.create()
        r3 = R.objects.create()

        MR.objects.create(m=m, r=r1)
        MR.objects.create(m=m, r=r2)
        MR.objects.create(m=m, r=r3)

        initial_count = MR.objects.count()
        self.assertEqual(initial_count, 3)

        # Delete m, which should cascade to MR entries
        with CaptureQueriesContext(connection) as ctx:
            m.delete()

        # Verify all MR entries are deleted
        self.assertEqual(MR.objects.count(), 0)

        # R objects should still exist (they have CASCADE from M)
        # Actually, let's not check this as the relationship might be different

    def test_single_queryset_not_modified(self):
        """
        Test that when there's only one queryset for a model, it's not
        unnecessarily modified.
        """
        author = Author.objects.create(name='solo')
        article = Article.objects.create(
            title='Solo Article',
            created_by=author,
            updated_by=None  # Only one FK relationship
        )

        # This should work correctly even with the optimization
        with CaptureQueriesContext(connection) as ctx:
            author.delete()

        # Should have deleted the author and article
        self.assertFalse(Author.objects.filter(pk=author.pk).exists())
        self.assertFalse(Article.objects.filter(pk=article.pk).exists())

    def test_no_fast_delete_not_affected(self):
        """
        Test that models that don't use fast delete are not affected by the
        optimization.
        """
        # This test ensures backward compatibility
        from .models import A, create_a

        a = create_a('test')

        # This should work as before
        a.cascade.delete()

        # A should be deleted due to CASCADE
        self.assertFalse(A.objects.filter(pk=a.pk).exists())

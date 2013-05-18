from django.test import TestCase
from django.db import models
from django.db.models.loading import BaseAppCache
from django.db.migrations.state import ProjectState


class StateTests(TestCase):
    """
    Tests state construction, rendering and modification by operations.
    """

    def test_create(self):
        """
        Tests making a ProjectState from an AppCache
        """
        new_app_cache = BaseAppCache()

        class Author(models.Model):
            name = models.CharField(max_length=255)
            bio = models.TextField()
            age = models.IntegerField(blank=True, null=True)
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache

        class Book(models.Model):
            title = models.CharField(max_length=1000)
            author = models.ForeignKey(Author)
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache

        project_state = ProjectState.from_app_cache(new_app_cache)
        author_state = project_state.models['migrations', 'author']
        book_state = project_state.models['migrations', 'book']
        
        self.assertEqual(author_state.app_label, "migrations")
        self.assertEqual(author_state.name, "Author")
        self.assertEqual([x for x, y in author_state.fields], ["id", "name", "bio", "age"])
        self.assertEqual(author_state.fields[1][1].max_length, 255)
        self.assertEqual(author_state.fields[2][1].null, False)
        self.assertEqual(author_state.fields[3][1].null, True)
        self.assertEqual(author_state.bases, (models.Model, ))

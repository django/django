from django.test import TestCase
from django.db import models
from django.db.models.loading import BaseAppCache
from django.db.migrations.state import ProjectState, ModelState


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
                unique_together = ["name", "bio"]

        class Book(models.Model):
            title = models.CharField(max_length=1000)
            author = models.ForeignKey(Author)
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache
                verbose_name = "tome"
                db_table = "test_tome"

        project_state = ProjectState.from_app_cache(new_app_cache)
        author_state = project_state.models['migrations', 'author']
        book_state = project_state.models['migrations', 'book']
        
        self.assertEqual(author_state.app_label, "migrations")
        self.assertEqual(author_state.name, "Author")
        self.assertEqual([x for x, y in author_state.fields], ["id", "name", "bio", "age"])
        self.assertEqual(author_state.fields[1][1].max_length, 255)
        self.assertEqual(author_state.fields[2][1].null, False)
        self.assertEqual(author_state.fields[3][1].null, True)
        self.assertEqual(author_state.options, {"unique_together": set(("name", "bio"))})
        self.assertEqual(author_state.bases, (models.Model, ))
        
        self.assertEqual(book_state.app_label, "migrations")
        self.assertEqual(book_state.name, "Book")
        self.assertEqual([x for x, y in book_state.fields], ["id", "title", "author"])
        self.assertEqual(book_state.fields[1][1].max_length, 1000)
        self.assertEqual(book_state.fields[2][1].null, False)
        self.assertEqual(book_state.options, {"verbose_name": "tome", "db_table": "test_tome"})
        self.assertEqual(book_state.bases, (models.Model, ))

    def test_render(self):
        """
        Tests rendering a ProjectState into an AppCache.
        """
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("hidden", models.BooleanField()),
            ],
            {},
            None,
        ))

        new_app_cache = project_state.render()
        self.assertEqual(new_app_cache.get_model("migrations", "Tag")._meta.get_field_by_name("name")[0].max_length, 100)
        self.assertEqual(new_app_cache.get_model("migrations", "Tag")._meta.get_field_by_name("hidden")[0].null, False)

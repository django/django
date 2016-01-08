from django.apps.registry import Apps
from django.db import models

# Since the test database doesn't have tablespaces, it's impossible for Django
# to create the tables for models where db_tablespace is set. To avoid this
# problem, we register the models to another apps registry.
tablespace_apps = Apps()


class ScientistRef(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        apps = tablespace_apps


class ArticleRef(models.Model):
    title = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True)
    authors = models.ManyToManyField(ScientistRef, related_name='articles_written_set')
    reviewers = models.ManyToManyField(ScientistRef, related_name='articles_reviewed_set')

    class Meta:
        apps = tablespace_apps


class Scientist(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'model_options_scientistref'
        db_tablespace = 'tbl_tbsp'
        apps = tablespace_apps


class Article(models.Model):
    title = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True, db_tablespace='idx_tbsp')
    authors = models.ManyToManyField(
        Scientist, related_name='articles_written_set', db_table='model_options_articleref_authors'
    )
    reviewers = models.ManyToManyField(
        Scientist, related_name='articles_reviewed_set',
        db_table='model_options_articleref_reviewers', db_tablespace='idx_tbsp',
    )

    class Meta:
        db_table = 'model_options_articleref'
        db_tablespace = 'tbl_tbsp'
        apps = tablespace_apps

Authors = Article._meta.get_field('authors').remote_field.through
Reviewers = Article._meta.get_field('reviewers').remote_field.through

from django.db import models


# Since the test database doesn't have tablespaces, it's impossible for Django
# to create the tables for models where db_tablespace is set. To avoid this
# problem, we mark the models as unmanaged, and temporarily revert them to
# managed during each test. We also set them to use the same tables as the
# "reference" models to avoid errors when other tests run 'migrate'
# (proxy_models_inheritance does).


class ScientistRef(models.Model):
    name = models.CharField(max_length=50)


class ArticleRef(models.Model):
    title = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True)
    authors = models.ManyToManyField(ScientistRef, related_name='articles_written_set')
    reviewers = models.ManyToManyField(ScientistRef, related_name='articles_reviewed_set')


class Scientist(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'model_options_scientistref'
        db_tablespace = 'tbl_tbsp'
        managed = False


class Article(models.Model):
    title = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True, db_tablespace='idx_tbsp')
    authors = models.ManyToManyField(Scientist, related_name='articles_written_set')
    reviewers = models.ManyToManyField(Scientist, related_name='articles_reviewed_set', db_tablespace='idx_tbsp')

    class Meta:
        db_table = 'model_options_articleref'
        db_tablespace = 'tbl_tbsp'
        managed = False


# Also set the tables for automatically created models

Authors = Article._meta.get_field('authors').remote_field.through
Authors._meta.db_table = 'model_options_articleref_authors'

Reviewers = Article._meta.get_field('reviewers').remote_field.through
Reviewers._meta.db_table = 'model_options_articleref_reviewers'

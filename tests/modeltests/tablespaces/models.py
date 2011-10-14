from django.db import models

# Since the test database doesn't have tablespaces, it's impossible for Django
# to create the tables for models where db_tablespace is set. To avoid this
# problem, we mark the models as unmanaged, and temporarily revert them to
# managed during each tes. See setUp and tearDown -- it isn't possible to use
# setUpClass and tearDownClass because they're called before Django flushes the
# tables, so Django attempts to flush a non-existing table.

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
        db_tablespace = 'tbl_tbsp'
        managed = False

class Article(models.Model):
    title = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True, db_tablespace='idx_tbsp')
    authors = models.ManyToManyField(Scientist, related_name='articles_written_set')
    reviewers = models.ManyToManyField(Scientist, related_name='articles_reviewed_set', db_tablespace='idx_tbsp')
    class Meta:
        db_tablespace = 'tbl_tbsp'
        managed = False

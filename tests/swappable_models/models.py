from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=100)
    publication_date = models.DateField()

    class Meta:
        swappable = "TEST_ARTICLE_MODEL"


class AlternateArticle(models.Model):
    title = models.CharField(max_length=100)
    publication_date = models.DateField()
    byline = models.CharField(max_length=100)

from django.db import models
from django.utils import timezone


class Article(models.Model):
    title = models.CharField(max_length=100)
    publication_date = models.DateField()
    publication_datetime = models.DateTimeField(default=timezone.now())

    categories = models.ManyToManyField("Category", related_name="articles")

    def __str__(self):
        return self.title


class Comment(models.Model):
    article = models.ForeignKey(Article, models.CASCADE, related_name="comments")
    text = models.TextField()
    publication_date = models.DateField()
    approval_date = models.DateField(null=True)

    def __str__(self):
        return 'Comment to %s (%s)' % (self.article.title, self.publication_date)


class Category(models.Model):
    name = models.CharField(max_length=255)

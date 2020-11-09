from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    published_on = models.DateField(null=True)

    categories = models.ManyToManyField("Category", related_name="articles")


class Comment(models.Model):
    article = models.ForeignKey(Article, models.CASCADE, related_name="comments")
    text = models.TextField()
    pub_date = models.DateTimeField()
    approval_date = models.DateTimeField(null=True)


class Category(models.Model):
    name = models.CharField(max_length=255)

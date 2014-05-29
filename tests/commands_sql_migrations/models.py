from django.db import models


class Comment(models.Model):
    pass


class Book(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    comments = models.ManyToManyField(Comment)

from django.db import models


class Author(models.Model):
    name = models.TextField()


class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)


class Bio(models.Model):
    author = models.OneToOneField(
        Author,
        models.CASCADE,
        primary_key=True,
    )

    text = models.TextField()

from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=20)
    age = models.IntegerField(null=True)
    birthdate = models.DateField(null=True)
    average_rating = models.FloatField(null=True)


class Article(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)


class MySQLUnixTimestamp(models.Model):
    timestamp = models.PositiveIntegerField()

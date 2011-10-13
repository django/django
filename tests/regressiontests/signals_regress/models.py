from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

class Book(models.Model):
    name = models.CharField(max_length=20)
    authors = models.ManyToManyField(Author)

    def __unicode__(self):
        return self.name

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Comment(models.Model):
    def __str__(self):
        return super(Comment, self).__str__()


@python_2_unicode_compatible
class Book(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    comments = models.ManyToManyField(Comment)

    def __str__(self):
        return super(Book, self).__str__()

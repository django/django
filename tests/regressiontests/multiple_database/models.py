from django.conf import settings
from django.db import models, DEFAULT_DB_ALIAS

class Book(models.Model):
    title = models.CharField(max_length=100)
    published = models.DateField()
    authors = models.ManyToManyField('Author')

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)

class Author(models.Model):
    name = models.CharField(max_length=100)
    favourite_book = models.ForeignKey(Book, null=True, related_name='favourite_of')

    def __unicode__(self):
        return self.name

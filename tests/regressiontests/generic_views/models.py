from django.db import models

class Artist(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('artist_detail', (), {'pk': self.id})

class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

class Book(models.Model):
    name = models.CharField(max_length=300)
    slug = models.SlugField()
    pages = models.IntegerField()
    authors = models.ManyToManyField(Author)
    pubdate = models.DateField()

    class Meta:
        ordering = ['-pubdate']

    def __unicode__(self):
        return self.name

class Page(models.Model):
    content = models.TextField()
    template = models.CharField(max_length=300)

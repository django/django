from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Entry(models.Model):
    title = models.CharField(max_length=200)
    updated = models.DateTimeField()
    published = models.DateTimeField()

    class Meta:
        ordering = ('updated',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return "/blog/%s/" % self.pk


@python_2_unicode_compatible
class Article(models.Model):
    title = models.CharField(max_length=200)
    entry = models.ForeignKey(Entry, models.CASCADE)

    def __str__(self):
        return self.title

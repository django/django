from django.db import models


class Entry(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateTimeField()

    class Meta:
        ordering = ('date',)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return "/blog/%s/" % self.pk


class Article(models.Model):
    title = models.CharField(max_length=200)
    entry = models.ForeignKey(Entry)

    def __unicode__(self):
        return self.title


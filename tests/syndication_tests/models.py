from django.db import models


class Entry(models.Model):
    title = models.CharField(max_length=200)
    updated = models.DateTimeField()
    published = models.DateTimeField()

    class Meta:
        ordering = ("updated",)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return "/blog/%s/" % self.pk


class Article(models.Model):
    title = models.CharField(max_length=200)
    entry = models.ForeignKey(Entry, models.CASCADE)
    updated = models.DateTimeField()
    published = models.DateTimeField()

    class Meta:
        ordering = ["updated"]

from django.db import models


class Site(models.Model):
    name = models.CharField(max_length=100)


class Article(models.Model):
    sites = models.ManyToManyField(Site)
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField("model_package.Publication", blank=True)

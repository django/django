from django.contrib.sites.models import Site
from django.db import models


class Article(models.Model):
    sites = models.ManyToManyField(Site)
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField("model_package.Publication", blank=True,)

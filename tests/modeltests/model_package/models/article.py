from django.db import models
from django.contrib.sites.models import Site

class Article(models.Model):
    sites = models.ManyToManyField(Site)
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField("model_package.Publication", null=True, blank=True,)

    class Meta:
        app_label = 'model_package'

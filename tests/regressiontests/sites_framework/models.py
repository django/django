from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

@python_2_unicode_compatible
class AbstractArticle(models.Model):
    title = models.CharField(max_length=50)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

class SyndicatedArticle(AbstractArticle):
    sites = models.ManyToManyField(Site)

class ExclusiveArticle(AbstractArticle):
    site = models.ForeignKey(Site)

class CustomArticle(AbstractArticle):
    places_this_article_should_appear = models.ForeignKey(Site)

    objects = models.Manager()
    on_site = CurrentSiteManager("places_this_article_should_appear")

class InvalidArticle(AbstractArticle):
    site = models.ForeignKey(Site)

    objects = models.Manager()
    on_site = CurrentSiteManager("places_this_article_should_appear")

class ConfusedArticle(AbstractArticle):
    site = models.IntegerField()

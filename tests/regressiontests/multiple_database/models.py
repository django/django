from django.conf import settings
from django.db import models, DEFAULT_DB_ALIAS

class Book(models.Model):
    title = models.CharField(max_length=100)
    published = models.DateField()

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)

if len(settings.DATABASES) > 1:
    article_using = filter(lambda o: o != DEFAULT_DB_ALIAS, settings.DATABASES.keys())[0]
    class Article(models.Model):
        title = models.CharField(max_length=100)

        def __unicode__(self):
            return self.title

        class Meta:
            ordering = ('title',)
            using = article_using

from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __unicode__(self):
        return self.headline

    class Meta:
        app_label = 'fixtures_model_package'
        ordering = ('-pub_date', 'headline')

class Book(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name',)

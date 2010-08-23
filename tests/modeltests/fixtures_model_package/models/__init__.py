from django.db import models
from django.conf import settings

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __unicode__(self):
        return self.headline

    class Meta:
        app_label = 'fixtures_model_package'
        ordering = ('-pub_date', 'headline')


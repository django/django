from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline

    class Meta:
        app_label = 'fixtures_model_package'
        ordering = ('-pub_date', 'headline')

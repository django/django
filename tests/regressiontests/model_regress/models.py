# coding: utf-8
from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100, default='Default headline')
    pub_date = models.DateTimeField()

    class Meta:
        ordering = ('pub_date','headline')
        # A utf-8 verbose name (Ångström's Articles) to test they are valid.
        verbose_name = "\xc3\x85ngstr\xc3\xb6m's Articles"

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS': "" }

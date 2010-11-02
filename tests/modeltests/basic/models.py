# coding: utf-8
"""
1. Bare-bones model

This is a basic model with only two non-primary-key fields.
"""
from django.db import models, DEFAULT_DB_ALIAS

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    class Meta:
        ordering = ('pub_date','headline')

    def __unicode__(self):
        return self.headline

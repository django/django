# coding: utf-8
"""
1. Bare-bones model

This is a basic model with only two non-primary-key fields.
"""
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    class Meta:
        ordering = ('pub_date','headline')

    def __str__(self):
        return self.headline

@python_2_unicode_compatible
class SelfRef(models.Model):
    selfref = models.ForeignKey('self', null=True, blank=True,
                                related_name='+')

    def __str__(self):
        return SelfRef.objects.get(selfref=self).pk

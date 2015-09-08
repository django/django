# coding: utf-8
"""
Pre-save method

You can define a method that will preprocess the value just before saving.
This test ensure the method is always called, regardless the arguments of
the save method.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Article(models.Model):
    update_date = models.DateTimeField(auto_now=True)

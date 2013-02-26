"""
XX. Model inheritance

Model inheritance across apps can result in models with the same name resulting
in the need for an %(app_label)s format string. This app specifically tests
this feature by redefining the Copy model from model_inheritance/models.py
"""

from __future__ import absolute_import

from django.db import models

from model_inheritance.models import NamedURL
from django.utils.encoding import python_2_unicode_compatible

#
# Abstract base classes with related models
#
@python_2_unicode_compatible
class Copy(NamedURL):
    content = models.TextField()

    def __str__(self):
        return self.content

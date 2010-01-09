"""
XX. Model inheritance

Model inheritance across apps can result in models with the same name resulting
in the need for an %(app_label)s format string. This app specifically tests
this feature by redefining the Copy model from model_inheritance/models.py
"""

from django.db import models
from modeltests.model_inheritance.models import NamedURL

#
# Abstract base classes with related models
#
class Copy(NamedURL):
    content = models.TextField()

    def __unicode__(self):
        return self.content

"""

Model inheritance across apps can result in models with the same name,
requiring an %(app_label)s format string. This app tests this feature by
redefining the Copy model from model_inheritance/models.py.
"""

from model_inheritance.models import NamedURL

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Copy(NamedURL):
    content = models.TextField()

    def __str__(self):
        return self.content

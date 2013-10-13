from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Category(models.Model):
    name = models.CharField(max_length=100)

    def next(self):
        return self


class Thing(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category)

python_2_unicode_compatible_failed = False
try:
    @python_2_unicode_compatible
    class NotStrModel(models.Model):
        name = models.CharField(max_length=100)

except NotImplementedError:
    python_2_unicode_compatible_failed = True

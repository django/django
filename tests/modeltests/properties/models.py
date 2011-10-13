"""
22. Using properties on models

Use properties on models just like on any other Python object.
"""

from django.db import models


class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def _get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def _set_full_name(self, combined_name):
        self.first_name, self.last_name = combined_name.split(' ', 1)

    full_name = property(_get_full_name)

    full_name_2 = property(_get_full_name, _set_full_name)

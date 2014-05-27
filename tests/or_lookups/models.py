"""
19. OR lookups

To perform an OR lookup, or a lookup that combines ANDs and ORs, combine
``QuerySet`` objects using ``&`` and ``|`` operators.

Alternatively, use positional arguments, and pass one or more expressions of
clauses using the variable ``freedom.db.models.Q`` (or any object with an
``add_to_query`` method).
"""

from freedom.db import models
from freedom.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()

    class Meta:
        ordering = ('pub_date',)

    def __str__(self):
        return self.headline

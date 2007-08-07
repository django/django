# coding: utf-8
from django.db import models

CHOICES = (
    (1, 'first'),
    (2, 'second'),
)

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()
    status = models.IntegerField(blank=True, null=True, choices=CHOICES)

    class Meta:
        ordering = ('pub_date','headline')
        # A utf-8 verbose name (Ångström's Articles) to test they are valid.
        verbose_name = "\xc3\x85ngstr\xc3\xb6m's Articles"

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS': """
(NOTE: Part of the regression test here is merely parsing the model
declaration. The verbose_name, in particular, did not always work.)

An empty choice field should return None for the display name.

>>> from datetime import datetime
>>> a = Article(headline="Look at me!", pub_date=datetime.now())
>>> a.save()
>>> a.get_status_display() is None
True
"""
}

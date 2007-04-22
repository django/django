# -*- coding: utf-8 -*-
"""
2. Adding __str__() or __unicode__() to models

Although it's not a strict requirement, each model should have a ``__str__()``
method to return a "human-readable" representation of the object. Do this not
only for your own sanity when dealing with the interactive prompt, but also
because objects' representations are used throughout Django's
automatically-generated admin.

For international applications, you should write ``__unicode__``() method
instead.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline

class InternationalArticle(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateTimeField()

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS':ur"""
# Create an Article.
>>> from datetime import datetime
>>> a = Article(headline='Area man programs in Python', pub_date=datetime(2005, 7, 28))
>>> a.save()

>>> str(a)
'Area man programs in Python'

>>> a
<Article: Area man programs in Python>

>>> a1 = InternationalArticle(headline=u'Girl wins €12.500 in lottery', pub_date=datetime(2005, 7, 28))

# The default str() output will be the UTF-8 encoded output of __unicode__().
>>> str(a1)
'Girl wins \xe2\x82\xac12.500 in lottery'
"""}

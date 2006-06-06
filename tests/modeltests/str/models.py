"""
2. Adding __str__() to models

Although it's not a strict requirement, each model should have a ``__str__()``
method to return a "human-readable" representation of the object. Do this not
only for your own sanity when dealing with the interactive prompt, but also
because objects' representations are used throughout Django's
automatically-generated admin.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline

API_TESTS = """
# Create an Article.
>>> from datetime import datetime
>>> a = Article(headline='Area man programs in Python', pub_date=datetime(2005, 7, 28))
>>> a.save()

>>> str(a)
'Area man programs in Python'

>>> a
<Article: Area man programs in Python>
"""

"""
8. get_latest_by

Models can have a ``get_latest_by`` attribute, which should be set to the name
of a DateField or DateTimeField. If ``get_latest_by`` exists, the model's
module will get a ``get_latest()`` function, which will return the latest
object in the database according to that field. "Latest" means "having the
date farthest into the future."
"""

from django.core import meta

class Article(meta.Model):
    fields = (
        meta.CharField('headline', maxlength=100),
        meta.DateTimeField('pub_date'),
    )
    get_latest_by = 'pub_date'

    def __repr__(self):
        return self.headline

API_TESTS = """
# Because no Articles exist yet, get_latest() raises ArticleDoesNotExist.
>>> articles.get_latest()
Traceback (most recent call last):
    ...
ArticleDoesNotExist: Article does not exist for {'order_by': ('-pub_date',), 'limit': 1}

# Create a couple of Articles.
>>> from datetime import datetime
>>> a1 = articles.Article(id=None, headline='Article 1', pub_date=datetime(2005, 7, 26))
>>> a1.save()
>>> a2 = articles.Article(id=None, headline='Article 2', pub_date=datetime(2005, 7, 27))
>>> a2.save()
>>> a3 = articles.Article(id=None, headline='Article 3', pub_date=datetime(2005, 7, 27))
>>> a3.save()
>>> a4 = articles.Article(id=None, headline='Article 4', pub_date=datetime(2005, 7, 28))
>>> a4.save()

# Get the latest Article.
>>> articles.get_latest()
Article 4
"""

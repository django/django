"""
6. Specifying ordering

Specify default ordering for a model using the ``ordering`` attribute, which
should be a list or tuple of field names. This tells Django how to order the
results of ``get_list()`` and other similar functions.

If a field name in ``ordering`` starts with a hyphen, that field will be
ordered in descending order. Otherwise, it'll be ordered in ascending order.
The special-case field name ``"?"`` specifies random order.

The ordering attribute is not required. If you leave it off, ordering will be
undefined -- not random, just undefined.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateTimeField()
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a couple of Articles.
>>> from datetime import datetime
>>> a1 = Article(headline='Article 1', pub_date=datetime(2005, 7, 26))
>>> a1.save()
>>> a2 = Article(headline='Article 2', pub_date=datetime(2005, 7, 27))
>>> a2.save()
>>> a3 = Article(headline='Article 3', pub_date=datetime(2005, 7, 27))
>>> a3.save()
>>> a4 = Article(headline='Article 4', pub_date=datetime(2005, 7, 28))
>>> a4.save()

# By default, articles.get_list() orders by pub_date descending, then
# headline ascending.
>>> list(Article.objects)
[Article 4, Article 2, Article 3, Article 1]

# Override ordering with order_by, which is in the same format as the ordering
# attribute in models.
>>> list(Article.objects.order_by('headline'))
[Article 1, Article 2, Article 3, Article 4]
>>> list(Article.objects.order_by('pub_date', '-headline')
[Article 1, Article 3, Article 2, Article 4]

# Use the "limit" parameter to limit the results.
>>> list(Article.objects.order_by('headline')[:3])
[Article 1, Article 2]

# Use the "offset" parameter with "limit" to offset the result list.
>>> list(Article.objects.order_by('headline')[1:3])
[Article 2, Article 3]

# Use '?' to order randomly. (We're using [...] in the output to indicate we
# don't know what order the output will be in.
>>> list(Article.objects.order_by('?'))
[...]
"""

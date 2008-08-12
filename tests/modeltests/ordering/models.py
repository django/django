"""
6. Specifying ordering

Specify default ordering for a model using the ``ordering`` attribute, which
should be a list or tuple of field names. This tells Django how to order
``QuerySet`` results.

If a field name in ``ordering`` starts with a hyphen, that field will be
ordered in descending order. Otherwise, it'll be ordered in ascending order.
The special-case field name ``"?"`` specifies random order.

The ordering attribute is not required. If you leave it off, ordering will be
undefined -- not random, just undefined.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS':"""
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

# By default, Article.objects.all() orders by pub_date descending, then
# headline ascending.
>>> Article.objects.all()
[<Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 1>]

# Override ordering with order_by, which is in the same format as the ordering
# attribute in models.
>>> Article.objects.order_by('headline')
[<Article: Article 1>, <Article: Article 2>, <Article: Article 3>, <Article: Article 4>]
>>> Article.objects.order_by('pub_date', '-headline')
[<Article: Article 1>, <Article: Article 3>, <Article: Article 2>, <Article: Article 4>]

# Only the last order_by has any effect (since they each override any previous
# ordering).
>>> Article.objects.order_by('id')
[<Article: Article 1>, <Article: Article 2>, <Article: Article 3>, <Article: Article 4>]
>>> Article.objects.order_by('id').order_by('-headline')
[<Article: Article 4>, <Article: Article 3>, <Article: Article 2>, <Article: Article 1>]

# Use the 'stop' part of slicing notation to limit the results.
>>> Article.objects.order_by('headline')[:2]
[<Article: Article 1>, <Article: Article 2>]

# Use the 'stop' and 'start' parts of slicing notation to offset the result list.
>>> Article.objects.order_by('headline')[1:3]
[<Article: Article 2>, <Article: Article 3>]

# Getting a single item should work too:
>>> Article.objects.all()[0]
<Article: Article 4>

# Use '?' to order randomly. (We're using [...] in the output to indicate we
# don't know what order the output will be in.
>>> Article.objects.order_by('?')
[...]

# Ordering can be reversed using the reverse() method on a queryset. This
# allows you to extract things like "the last two items" (reverse and then
# take the first two).
>>> Article.objects.all().reverse()[:2]
[<Article: Article 1>, <Article: Article 3>]
"""}

"""
16. Many-to-one relationships that can be null

To define a many-to-one relationship, use ``ForeignKey()`` with ``null=True`` .
"""

from django.core import meta

class Reporter(meta.Model):
    name = meta.CharField(maxlength=30)

    def __repr__(self):
        return self.name

class Article(meta.Model):
    headline = meta.CharField(maxlength=100)
    reporter = meta.ForeignKey(Reporter, null=True)

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a Reporter.
>>> r = reporters.Reporter(name='John Smith')
>>> r.save()

# Create an Article.
>>> a = articles.Article(headline="First", reporter=r)
>>> a.save()

>>> a.reporter_id
1

>>> a.get_reporter()
John Smith

# Article objects have access to their related Reporter objects.
>>> r = a.get_reporter()

# Create an Article via the Reporter object.
>>> a2 = r.add_article(headline="Second")
>>> a2
Second
>>> a2.reporter_id
1

# Reporter objects have access to their related Article objects.
>>> r.get_article_list(order_by=['headline'])
[First, Second]
>>> r.get_article(headline__startswith='Fir')
First
>>> r.get_article_count()
2

# Create an Article with no Reporter by passing "reporter=None".
>>> a3 = articles.Article(headline="Third", reporter=None)
>>> a3.save()
>>> a3.id
3
>>> a3.reporter_id
>>> print a3.reporter_id
None
>>> a3 = articles.get_object(pk=3)
>>> print a3.reporter_id
None

# An article's get_reporter() method throws ReporterDoesNotExist
# if the reporter is set to None.
>>> a3.get_reporter()
Traceback (most recent call last):
    ...
ReporterDoesNotExist

# To retrieve the articles with no reporters set, use "reporter__isnull=True".
>>> articles.get_list(reporter__isnull=True)
[Third]
"""

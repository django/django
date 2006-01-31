"""
16. Many-to-one relationships that can be null

To define a many-to-one relationship that can have a null foreign key, use
``ForeignKey()`` with ``null=True`` .
"""

from django.db import models

class Reporter(models.Model):
    name = models.CharField(maxlength=30)

    def __repr__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    reporter = models.ForeignKey(Reporter, null=True)

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a Reporter.
>>> r = Reporter(name='John Smith')
>>> r.save()

# Create an Article.
>>> a = Article(headline="First", reporter=r)
>>> a.save()

>>> a.reporter.id
1

>>> a.reporter
John Smith

# Article objects have access to their related Reporter objects.
>>> r = a.reporter

# Create an Article via the Reporter object.
>>> a2 = r.article_set.add(headline="Second")
>>> a2
Second
>>> a2.reporter.id
1

# Reporter objects have access to their related Article objects.
>>> r.article_set.order_by('headline')
[First, Second]
>>> r.article_set.filter(headline__startswith='Fir')
First
>>> r.article_set.count()
2

# Create an Article with no Reporter by passing "reporter=None".
>>> a3 = Article(headline="Third", reporter=None)
>>> a3.save()
>>> a3.id
3
>>> a3.reporter.id
>>> print a3.reporter.id
None
>>> a3 = Article.objects.get(pk=3)
>>> print a3.reporter.id
None

# Accessing an article's 'reporter' attribute throws ReporterDoesNotExist
# if the reporter is set to None.
>>> a3.reporter
Traceback (most recent call last):
    ...
DoesNotExist

# To retrieve the articles with no reporters set, use "reporter__isnull=True".
>>> Article.objects.filter(reporter__isnull=True)
[Third]
"""

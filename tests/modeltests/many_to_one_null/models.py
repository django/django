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
>>> a3 = Article(headline="Third", reporter=None)
>>> a3.save()
>>> a3.id
3
>>> a3.reporter_id
>>> print a3.reporter_id
None
>>> a3 = Article.objects.get_object(pk=3)
>>> print a3.reporter_id
None

# An article's get_reporter() method throws ReporterDoesNotExist
# if the reporter is set to None.
>>> a3.get_reporter()
Traceback (most recent call last):
    ...
DoesNotExist

# To retrieve the articles with no reporters set, use "reporter__isnull=True".
>>> Article.objects.get_list(reporter__isnull=True)
[Third]
"""

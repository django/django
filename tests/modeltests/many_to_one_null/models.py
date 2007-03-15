"""
16. Many-to-one relationships that can be null

To define a many-to-one relationship that can have a null foreign key, use
``ForeignKey()`` with ``null=True`` .
"""

from django.db import models

class Reporter(models.Model):
    name = models.CharField(maxlength=30)

    def __str__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    reporter = models.ForeignKey(Reporter, null=True)

    class Meta:
        ordering = ('headline',)

    def __str__(self):
        return self.headline

__test__ = {'API_TESTS':"""
# Create a Reporter.
>>> r = Reporter(name='John Smith')
>>> r.save()

# Create an Article.
>>> a = Article(headline="First", reporter=r)
>>> a.save()

>>> a.reporter.id
1

>>> a.reporter
<Reporter: John Smith>

# Article objects have access to their related Reporter objects.
>>> r = a.reporter

# Create an Article via the Reporter object.
>>> a2 = r.article_set.create(headline="Second")
>>> a2
<Article: Second>
>>> a2.reporter.id
1

# Reporter objects have access to their related Article objects.
>>> r.article_set.all()
[<Article: First>, <Article: Second>]
>>> r.article_set.filter(headline__startswith='Fir')
[<Article: First>]
>>> r.article_set.count()
2

# Create an Article with no Reporter by passing "reporter=None".
>>> a3 = Article(headline="Third", reporter=None)
>>> a3.save()
>>> a3.id
3
>>> print a3.reporter
None

# Need to reget a3 to refresh the cache
>>> a3 = Article.objects.get(pk=3)
>>> print a3.reporter.id
Traceback (most recent call last):
    ...
AttributeError: 'NoneType' object has no attribute 'id'

# Accessing an article's 'reporter' attribute returns None
# if the reporter is set to None.
>>> print a3.reporter
None

# To retrieve the articles with no reporters set, use "reporter__isnull=True".
>>> Article.objects.filter(reporter__isnull=True)
[<Article: Third>]

# Set the reporter for the Third article
>>> r.article_set.add(a3)
>>> r.article_set.all()
[<Article: First>, <Article: Second>, <Article: Third>]

# Remove an article from the set, and check that it was removed.
>>> r.article_set.remove(a3)
>>> r.article_set.all()
[<Article: First>, <Article: Second>]
>>> Article.objects.filter(reporter__isnull=True)
[<Article: Third>]

# Create another article and reporter
>>> r2 = Reporter(name='Paul Jones')
>>> r2.save()
>>> a4 = r2.article_set.create(headline='Fourth')
>>> r2.article_set.all()
[<Article: Fourth>]

# Try to remove a4 from a set it does not belong to
>>> r.article_set.remove(a4)
Traceback (most recent call last):
...
DoesNotExist: <Article: Fourth> is not related to <Reporter: John Smith>.

>>> r2.article_set.all()
[<Article: Fourth>]

# Use descriptor assignment to allocate ForeignKey. Null is legal, so
# existing members of set that are not in the assignment set are set null
>>> r2.article_set = [a2, a3]
>>> r2.article_set.all()
[<Article: Second>, <Article: Third>]

# Clear the rest of the set
>>> r.article_set.clear()
>>> r.article_set.all()
[]
>>> Article.objects.filter(reporter__isnull=True)
[<Article: First>, <Article: Fourth>]

"""}

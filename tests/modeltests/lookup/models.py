"""
7. The lookup API

This demonstrates features of the database API.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateTimeField()
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __str__(self):
        return self.headline

__test__ = {'API_TESTS':r"""
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
>>> a5 = Article(headline='Article 5', pub_date=datetime(2005, 8, 1, 9, 0))
>>> a5.save()
>>> a6 = Article(headline='Article 6', pub_date=datetime(2005, 8, 1, 8, 0))
>>> a6.save()
>>> a7 = Article(headline='Article 7', pub_date=datetime(2005, 7, 27))
>>> a7.save()

# Each QuerySet gets iterator(), which is a generator that "lazily" returns
# results using database-level iteration.
>>> for a in Article.objects.iterator():
...     print a.headline
Article 5
Article 6
Article 4
Article 2
Article 3
Article 7
Article 1

# iterator() can be used on any QuerySet.
>>> for a in Article.objects.filter(headline__endswith='4').iterator():
...     print a.headline
Article 4

# count() returns the number of objects matching search criteria.
>>> Article.objects.count()
7L
>>> Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).count()
3L
>>> Article.objects.filter(headline__startswith='Blah blah').count()
0L

# Date and date/time lookups can also be done with strings.
>>> Article.objects.filter(pub_date__exact='2005-07-27 00:00:00').count()
3L

# in_bulk() takes a list of IDs and returns a dictionary mapping IDs
# to objects.
>>> Article.objects.in_bulk([1, 2])
{1: <Article: Article 1>, 2: <Article: Article 2>}
>>> Article.objects.in_bulk([3])
{3: <Article: Article 3>}
>>> Article.objects.in_bulk([1000])
{}
>>> Article.objects.in_bulk([])
{}
>>> Article.objects.in_bulk('foo')
Traceback (most recent call last):
    ...
AssertionError: in_bulk() must be provided with a list of IDs.
>>> Article.objects.in_bulk()
Traceback (most recent call last):
    ...
TypeError: in_bulk() takes exactly 2 arguments (1 given)
>>> Article.objects.in_bulk(headline__startswith='Blah')
Traceback (most recent call last):
    ...
TypeError: in_bulk() got an unexpected keyword argument 'headline__startswith'

# values() returns a list of dictionaries instead of object instances -- and
# you can specify which fields you want to retrieve.
>>> Article.objects.values('headline')
[{'headline': 'Article 5'}, {'headline': 'Article 6'}, {'headline': 'Article 4'}, {'headline': 'Article 2'}, {'headline': 'Article 3'}, {'headline': 'Article 7'}, {'headline': 'Article 1'}]
>>> Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).values('id')
[{'id': 2}, {'id': 3}, {'id': 7}]
>>> list(Article.objects.values('id', 'headline')) == [{'id': 5, 'headline': 'Article 5'}, {'id': 6, 'headline': 'Article 6'}, {'id': 4, 'headline': 'Article 4'}, {'id': 2, 'headline': 'Article 2'}, {'id': 3, 'headline': 'Article 3'}, {'id': 7, 'headline': 'Article 7'}, {'id': 1, 'headline': 'Article 1'}]
True

>>> for d in Article.objects.values('id', 'headline'):
...     i = d.items()
...     i.sort()
...     i
[('headline', 'Article 5'), ('id', 5)]
[('headline', 'Article 6'), ('id', 6)]
[('headline', 'Article 4'), ('id', 4)]
[('headline', 'Article 2'), ('id', 2)]
[('headline', 'Article 3'), ('id', 3)]
[('headline', 'Article 7'), ('id', 7)]
[('headline', 'Article 1'), ('id', 1)]

# You can use values() with iterator() for memory savings, because iterator()
# uses database-level iteration.
>>> for d in Article.objects.values('id', 'headline').iterator():
...     i = d.items()
...     i.sort()
...     i
[('headline', 'Article 5'), ('id', 5)]
[('headline', 'Article 6'), ('id', 6)]
[('headline', 'Article 4'), ('id', 4)]
[('headline', 'Article 2'), ('id', 2)]
[('headline', 'Article 3'), ('id', 3)]
[('headline', 'Article 7'), ('id', 7)]
[('headline', 'Article 1'), ('id', 1)]

# if you don't specify which fields, all are returned
>>> list(Article.objects.filter(id=5).values()) == [{'id': 5, 'headline': 'Article 5', 'pub_date': datetime(2005, 8, 1, 9, 0)}]
True

# Every DateField and DateTimeField creates get_next_by_FOO() and
# get_previous_by_FOO() methods.
# In the case of identical date values, these methods will use the ID as a
# fallback check. This guarantees that no records are skipped or duplicated.
>>> a1.get_next_by_pub_date()
<Article: Article 2>
>>> a2.get_next_by_pub_date()
<Article: Article 3>
>>> a2.get_next_by_pub_date(headline__endswith='6')
<Article: Article 6>
>>> a3.get_next_by_pub_date()
<Article: Article 7>
>>> a4.get_next_by_pub_date()
<Article: Article 6>
>>> a5.get_next_by_pub_date()
Traceback (most recent call last):
    ...
DoesNotExist: Article matching query does not exist.
>>> a6.get_next_by_pub_date()
<Article: Article 5>
>>> a7.get_next_by_pub_date()
<Article: Article 4>

>>> a7.get_previous_by_pub_date()
<Article: Article 3>
>>> a6.get_previous_by_pub_date()
<Article: Article 4>
>>> a5.get_previous_by_pub_date()
<Article: Article 6>
>>> a4.get_previous_by_pub_date()
<Article: Article 7>
>>> a3.get_previous_by_pub_date()
<Article: Article 2>
>>> a2.get_previous_by_pub_date()
<Article: Article 1>

# Underscores and percent signs have special meaning in the underlying
# SQL code, but Django handles the quoting of them automatically.
>>> a8 = Article(headline='Article_ with underscore', pub_date=datetime(2005, 11, 20))
>>> a8.save()
>>> Article.objects.filter(headline__startswith='Article')
[<Article: Article_ with underscore>, <Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 7>, <Article: Article 1>]
>>> Article.objects.filter(headline__startswith='Article_')
[<Article: Article_ with underscore>]

>>> a9 = Article(headline='Article% with percent sign', pub_date=datetime(2005, 11, 21))
>>> a9.save()
>>> Article.objects.filter(headline__startswith='Article')
[<Article: Article% with percent sign>, <Article: Article_ with underscore>, <Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 7>, <Article: Article 1>]
>>> Article.objects.filter(headline__startswith='Article%')
[<Article: Article% with percent sign>]

# exclude() is the opposite of filter() when doing lookups:
>>> Article.objects.filter(headline__contains='Article').exclude(headline__contains='with')
[<Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 7>, <Article: Article 1>]
>>> Article.objects.exclude(headline__startswith="Article_")
[<Article: Article% with percent sign>, <Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 7>, <Article: Article 1>]
>>> Article.objects.exclude(headline="Article 7")
[<Article: Article% with percent sign>, <Article: Article_ with underscore>, <Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 1>]

# Backslashes also have special meaning in the underlying SQL code, but Django
# automatically quotes them appropriately.
>>> a10 = Article(headline='Article with \\ backslash', pub_date=datetime(2005, 11, 22))
>>> a10.save()
>>> Article.objects.filter(headline__contains='\\')
[<Article: Article with \ backslash>]

# none() returns an EmptyQuerySet that behaves like any other QuerySet object
>>> Article.objects.none()
[]
>>> Article.objects.none().filter(headline__startswith='Article')
[]
>>> Article.objects.none().count()
0
>>> [article for article in Article.objects.none().iterator()]
[]

# using __in with an empty list should return an empty query set
>>> Article.objects.filter(id__in=[])
[]

>>> Article.objects.exclude(id__in=[])
[<Article: Article with \ backslash>, <Article: Article% with percent sign>, <Article: Article_ with underscore>, <Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 7>, <Article: Article 1>]

# Programming errors are pointed out with nice error messages
>>> Article.objects.filter(pub_date_year='2005').count()
Traceback (most recent call last):
    ...
TypeError: Cannot resolve keyword 'pub_date_year' into field

>>> Article.objects.filter(headline__starts='Article')
Traceback (most recent call last):
    ...
TypeError: Cannot resolve keyword 'headline__starts' into field

"""}

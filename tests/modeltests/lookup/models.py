"""
7. The lookup API

This demonstrates features of the database API.
"""

from django.db import models
from django.conf import settings

class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __unicode__(self):
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

# text matching tests for PostgreSQL 8.3
>>> Article.objects.filter(id__iexact='1')
[<Article: Article 1>]
>>> Article.objects.filter(pub_date__startswith='2005')
[<Article: Article 5>, <Article: Article 6>, <Article: Article 4>, <Article: Article 2>, <Article: Article 3>, <Article: Article 7>, <Article: Article 1>]

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

# count() should respect sliced query sets.
>>> articles = Article.objects.all()
>>> articles.count()
7L
>>> articles[:4].count()
4
>>> articles[1:100].count()
6L
>>> articles[10:100].count()
0

# Date and date/time lookups can also be done with strings.
>>> Article.objects.filter(pub_date__exact='2005-07-27 00:00:00').count()
3L

# in_bulk() takes a list of IDs and returns a dictionary mapping IDs
# to objects.
>>> arts = Article.objects.in_bulk([1, 2])
>>> arts[1]
<Article: Article 1>
>>> arts[2]
<Article: Article 2>
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
[{'headline': u'Article 5'}, {'headline': u'Article 6'}, {'headline': u'Article 4'}, {'headline': u'Article 2'}, {'headline': u'Article 3'}, {'headline': u'Article 7'}, {'headline': u'Article 1'}]
>>> Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).values('id')
[{'id': 2}, {'id': 3}, {'id': 7}]
>>> list(Article.objects.values('id', 'headline')) == [{'id': 5, 'headline': 'Article 5'}, {'id': 6, 'headline': 'Article 6'}, {'id': 4, 'headline': 'Article 4'}, {'id': 2, 'headline': 'Article 2'}, {'id': 3, 'headline': 'Article 3'}, {'id': 7, 'headline': 'Article 7'}, {'id': 1, 'headline': 'Article 1'}]
True

>>> for d in Article.objects.values('id', 'headline'):
...     i = d.items()
...     i.sort()
...     i
[('headline', u'Article 5'), ('id', 5)]
[('headline', u'Article 6'), ('id', 6)]
[('headline', u'Article 4'), ('id', 4)]
[('headline', u'Article 2'), ('id', 2)]
[('headline', u'Article 3'), ('id', 3)]
[('headline', u'Article 7'), ('id', 7)]
[('headline', u'Article 1'), ('id', 1)]

# You can use values() with iterator() for memory savings, because iterator()
# uses database-level iteration.
>>> for d in Article.objects.values('id', 'headline').iterator():
...     i = d.items()
...     i.sort()
...     i
[('headline', u'Article 5'), ('id', 5)]
[('headline', u'Article 6'), ('id', 6)]
[('headline', u'Article 4'), ('id', 4)]
[('headline', u'Article 2'), ('id', 2)]
[('headline', u'Article 3'), ('id', 3)]
[('headline', u'Article 7'), ('id', 7)]
[('headline', u'Article 1'), ('id', 1)]

# The values() method works with "extra" fields specified in extra(select).
>>> for d in Article.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_one'):
...     i = d.items()
...     i.sort()
...     i
[('id', 5), ('id_plus_one', 6)]
[('id', 6), ('id_plus_one', 7)]
[('id', 4), ('id_plus_one', 5)]
[('id', 2), ('id_plus_one', 3)]
[('id', 3), ('id_plus_one', 4)]
[('id', 7), ('id_plus_one', 8)]
[('id', 1), ('id_plus_one', 2)]
>>> data = {'id_plus_one': 'id+1', 'id_plus_two': 'id+2', 'id_plus_three': 'id+3',
...         'id_plus_four': 'id+4', 'id_plus_five': 'id+5', 'id_plus_six': 'id+6',
...         'id_plus_seven': 'id+7', 'id_plus_eight': 'id+8'}
>>> result = list(Article.objects.filter(id=1).extra(select=data).values(*data.keys()))[0]
>>> result = result.items()
>>> result.sort()
>>> result
[('id_plus_eight', 9), ('id_plus_five', 6), ('id_plus_four', 5), ('id_plus_one', 2), ('id_plus_seven', 8), ('id_plus_six', 7), ('id_plus_three', 4), ('id_plus_two', 3)]

# However, an exception FieldDoesNotExist will be thrown if you specify a
# non-existent field name in values() (a field that is neither in the model
# nor in extra(select)).
>>> Article.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_two')
Traceback (most recent call last):
    ...
FieldError: Cannot resolve keyword 'id_plus_two' into field. Choices are: headline, id, id_plus_one, pub_date

# If you don't specify field names to values(), all are returned.
>>> list(Article.objects.filter(id=5).values()) == [{'id': 5, 'headline': 'Article 5', 'pub_date': datetime(2005, 8, 1, 9, 0)}]
True

# values_list() is similar to values(), except that the results are returned as
# a list of tuples, rather than a list of dictionaries. Within each tuple, the
# order of the elemnts is the same as the order of fields in the values_list()
# call.
>>> Article.objects.values_list('headline')
[(u'Article 5',), (u'Article 6',), (u'Article 4',), (u'Article 2',), (u'Article 3',), (u'Article 7',), (u'Article 1',)]

>>> Article.objects.values_list('id').order_by('id')
[(1,), (2,), (3,), (4,), (5,), (6,), (7,)]
>>> Article.objects.values_list('id', flat=True).order_by('id')
[1, 2, 3, 4, 5, 6, 7]

>>> Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id')
[(1,), (2,), (3,), (4,), (5,), (6,), (7,)]
>>> Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id_plus_one', 'id')
[(2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7)]
>>> Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id', 'id_plus_one')
[(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]

>>> Article.objects.values_list('id', 'headline', flat=True)
Traceback (most recent call last):
...
TypeError: 'flat' is not valid when values_list is called with more than one field.

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
>>> Article.objects.filter(headline__startswith='Article').none()
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
FieldError: Cannot resolve keyword 'pub_date_year' into field. Choices are: headline, id, pub_date

>>> Article.objects.filter(headline__starts='Article')
Traceback (most recent call last):
    ...
FieldError: Join on field 'headline' not permitted.

# Create some articles with a bit more interesting headlines for testing field lookups:
>>> now = datetime.now()
>>> for a in Article.objects.all():
...     a.delete()
>>> a1 = Article(pub_date=now, headline='f')
>>> a1.save()
>>> a2 = Article(pub_date=now, headline='fo')
>>> a2.save()
>>> a3 = Article(pub_date=now, headline='foo')
>>> a3.save()
>>> a4 = Article(pub_date=now, headline='fooo')
>>> a4.save()
>>> a5 = Article(pub_date=now, headline='hey-Foo')
>>> a5.save()

# zero-or-more
>>> Article.objects.filter(headline__regex=r'fo*')
[<Article: f>, <Article: fo>, <Article: foo>, <Article: fooo>]
>>> Article.objects.filter(headline__iregex=r'fo*')
[<Article: f>, <Article: fo>, <Article: foo>, <Article: fooo>, <Article: hey-Foo>]

# one-or-more
>>> Article.objects.filter(headline__regex=r'fo+')
[<Article: fo>, <Article: foo>, <Article: fooo>]

# wildcard
>>> Article.objects.filter(headline__regex=r'fooo?')
[<Article: foo>, <Article: fooo>]

# and some more:
>>> a6 = Article(pub_date=now, headline='bar')
>>> a6.save()
>>> a7 = Article(pub_date=now, headline='AbBa')
>>> a7.save()
>>> a8 = Article(pub_date=now, headline='baz')
>>> a8.save()
>>> a9 = Article(pub_date=now, headline='baxZ')
>>> a9.save()

# leading anchor
>>> Article.objects.filter(headline__regex=r'^b')
[<Article: bar>, <Article: baxZ>, <Article: baz>]
>>> Article.objects.filter(headline__iregex=r'^a')
[<Article: AbBa>]

# trailing anchor
>>> Article.objects.filter(headline__regex=r'z$')
[<Article: baz>]
>>> Article.objects.filter(headline__iregex=r'z$')
[<Article: baxZ>, <Article: baz>]

# character sets
>>> Article.objects.filter(headline__regex=r'ba[rz]')
[<Article: bar>, <Article: baz>]
>>> Article.objects.filter(headline__regex=r'ba.[RxZ]')
[<Article: baxZ>]
>>> Article.objects.filter(headline__iregex=r'ba[RxZ]')
[<Article: bar>, <Article: baxZ>, <Article: baz>]

# and yet more:
>>> a10 = Article(pub_date=now, headline='foobar')
>>> a10.save()
>>> a11 = Article(pub_date=now, headline='foobaz')
>>> a11.save()
>>> a12 = Article(pub_date=now, headline='ooF')
>>> a12.save()
>>> a13 = Article(pub_date=now, headline='foobarbaz')
>>> a13.save()
>>> a14 = Article(pub_date=now, headline='zoocarfaz')
>>> a14.save()
>>> a15 = Article(pub_date=now, headline='barfoobaz')
>>> a15.save()
>>> a16 = Article(pub_date=now, headline='bazbaRFOO')
>>> a16.save()

# alternation
>>> Article.objects.filter(headline__regex=r'oo(f|b)')
[<Article: barfoobaz>, <Article: foobar>, <Article: foobarbaz>, <Article: foobaz>]
>>> Article.objects.filter(headline__iregex=r'oo(f|b)')
[<Article: barfoobaz>, <Article: foobar>, <Article: foobarbaz>, <Article: foobaz>, <Article: ooF>]
>>> Article.objects.filter(headline__regex=r'^foo(f|b)')
[<Article: foobar>, <Article: foobarbaz>, <Article: foobaz>]

# greedy matching
>>> Article.objects.filter(headline__regex=r'b.*az')
[<Article: barfoobaz>, <Article: baz>, <Article: bazbaRFOO>, <Article: foobarbaz>, <Article: foobaz>]
>>> Article.objects.filter(headline__iregex=r'b.*ar')
[<Article: bar>, <Article: barfoobaz>, <Article: bazbaRFOO>, <Article: foobar>, <Article: foobarbaz>]
"""}


if settings.DATABASE_ENGINE != 'mysql':
    __test__['API_TESTS'] += r"""
# grouping and backreferences
>>> Article.objects.filter(headline__regex=r'b(.).*b\1')
[<Article: barfoobaz>, <Article: bazbaRFOO>, <Article: foobarbaz>]
"""

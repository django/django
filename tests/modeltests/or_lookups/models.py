"""
19. OR lookups

To perform an OR lookup, or a lookup that combines ANDs and ORs,
combine QuerySet objects using & and | operators.

Alternatively, use positional arguments, and pass one or more expressions
of clauses using the variable ``django.db.models.Q`` (or any object with
a get_sql method).


"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateTimeField()

    class Meta:
       ordering = ('pub_date',)

    def __str__(self):
        return self.headline

__test__ = {'API_TESTS':"""
>>> from datetime import datetime
>>> from django.db.models import Q

>>> a1 = Article(headline='Hello', pub_date=datetime(2005, 11, 27))
>>> a1.save()

>>> a2 = Article(headline='Goodbye', pub_date=datetime(2005, 11, 28))
>>> a2.save()

>>> a3 = Article(headline='Hello and goodbye', pub_date=datetime(2005, 11, 29))
>>> a3.save()

>>> Article.objects.filter(headline__startswith='Hello') |  Article.objects.filter(headline__startswith='Goodbye')
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

>>> Article.objects.filter(Q(headline__startswith='Hello') | Q(headline__startswith='Goodbye'))
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

>>> Article.objects.filter(Q(headline__startswith='Hello') & Q(headline__startswith='Goodbye'))
[]

# You can shorten this syntax with code like the following,
# which is especially useful if building the query in stages:
>>> articles = Article.objects.all()
>>> articles.filter(headline__startswith='Hello') & articles.filter(headline__startswith='Goodbye')
[]

>>> articles.filter(headline__startswith='Hello') & articles.filter(headline__contains='bye')
[<Article: Hello and goodbye>]

>>> Article.objects.filter(Q(headline__contains='bye'), headline__startswith='Hello')
[<Article: Hello and goodbye>]

>>> Article.objects.filter(headline__contains='Hello') | Article.objects.filter(headline__contains='bye')
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

>>> Article.objects.filter(headline__iexact='Hello') | Article.objects.filter(headline__contains='ood')
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

>>> Article.objects.filter(Q(pk=1) | Q(pk=2))
[<Article: Hello>, <Article: Goodbye>]

>>> Article.objects.filter(Q(pk=1) | Q(pk=2) | Q(pk=3))
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

# You could also use "in" to accomplish the same as above.
>>> Article.objects.filter(pk__in=[1,2,3])
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

>>> Article.objects.filter(pk__in=[1,2,3,4])
[<Article: Hello>, <Article: Goodbye>, <Article: Hello and goodbye>]

# Passing "in" an empty list returns no results ...
>>> Article.objects.filter(pk__in=[])
[]

# ... but can return results if we OR it with another query.
>>> Article.objects.filter(Q(pk__in=[]) | Q(headline__icontains='goodbye'))
[<Article: Goodbye>, <Article: Hello and goodbye>]

# Q arg objects are ANDed
>>> Article.objects.filter(Q(headline__startswith='Hello'), Q(headline__contains='bye'))
[<Article: Hello and goodbye>]

# Q arg AND order is irrelevant
>>> Article.objects.filter(Q(headline__contains='bye'), headline__startswith='Hello')
[<Article: Hello and goodbye>]

# Try some arg queries with operations other than get_list
>>> Article.objects.get(Q(headline__startswith='Hello'), Q(headline__contains='bye'))
<Article: Hello and goodbye>

>>> Article.objects.filter(Q(headline__startswith='Hello') | Q(headline__contains='bye')).count()
3

>>> list(Article.objects.filter(Q(headline__startswith='Hello'), Q(headline__contains='bye')).values())
[{'headline': 'Hello and goodbye', 'pub_date': datetime.datetime(2005, 11, 29, 0, 0), 'id': 3}]

>>> Article.objects.filter(Q(headline__startswith='Hello')).in_bulk([1,2])
{1: <Article: Hello>}

# Demonstrating exclude with a Q object
>>> Article.objects.exclude(Q(headline__startswith='Hello'))
[<Article: Goodbye>]

# The 'complex_filter' method supports framework features such as
# 'limit_choices_to' which normally take a single dictionary of lookup arguments
# but need to support arbitrary queries via Q objects too.
>>> Article.objects.complex_filter({'pk': 1})
[<Article: Hello>]
>>> Article.objects.complex_filter(Q(pk=1) | Q(pk=2))
[<Article: Hello>, <Article: Goodbye>]
"""}

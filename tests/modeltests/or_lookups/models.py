"""
19. OR lookups

To perform an OR lookup, or a lookup that combines ANDs and ORs, use the
``complex`` keyword argument, and pass it an expression of clauses using the
variable ``django.db.models.Q`` (or any object with a get_sql method).
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateTimeField()
    class Meta:
       ordering = ('pub_date',)

    def __repr__(self):
        return self.headline

API_TESTS = """
>>> from datetime import datetime
>>> from django.db.models import Q

>>> a1 = Article(headline='Hello', pub_date=datetime(2005, 11, 27))
>>> a1.save()

>>> a2 = Article(headline='Goodbye', pub_date=datetime(2005, 11, 28))
>>> a2.save()

>>> a3 = Article(headline='Hello and goodbye', pub_date=datetime(2005, 11, 29))
>>> a3.save()

>>> Article.objects.get_list(complex=(Q(headline__startswith='Hello') | Q(headline__startswith='Goodbye')))
[Hello, Goodbye, Hello and goodbye]

>>> Article.objects.get_list(complex=(Q(headline__startswith='Hello') & Q(headline__startswith='Goodbye')))
[]

>>> Article.objects.get_list(complex=(Q(headline__startswith='Hello') & Q(headline__contains='bye')))
[Hello and goodbye]

>>> Article.objects.get_list(headline__startswith='Hello', complex=Q(headline__contains='bye'))
[Hello and goodbye]

>>> Article.objects.get_list(complex=(Q(headline__contains='Hello') | Q(headline__contains='bye')))
[Hello, Goodbye, Hello and goodbye]

>>> Article.objects.get_list(complex=(Q(headline__iexact='Hello') | Q(headline__contains='ood')))
[Hello, Goodbye, Hello and goodbye]

>>> Article.objects.get_list(complex=(Q(pk=1) | Q(pk=2)))
[Hello, Goodbye]

>>> Article.objects.get_list(complex=(Q(pk=1) | Q(pk=2) | Q(pk=3)))
[Hello, Goodbye, Hello and goodbye]

# Queries can use Q objects as args
>>> Article.objects.get_list(Q(headline__startswith='Hello'))
[Hello, Hello and goodbye]

# Q arg objects are ANDed 
>>> Article.objects.get_list(Q(headline__startswith='Hello'), Q(headline__contains='bye'))
[Hello and goodbye]

# Q arg AND order is irrelevant
>>> Article.objects.get_list(Q(headline__contains='bye'), headline__startswith='Hello')
[Hello and goodbye]

# QOrs are ok, as they ultimately resolve to a Q 
>>> Article.objects.get_list(Q(headline__contains='Hello') | Q(headline__contains='bye'))
[Hello, Goodbye, Hello and goodbye]

# Try some arg queries with operations other than get_list
>>> Article.objects.get_object(Q(headline__startswith='Hello'), Q(headline__contains='bye'))
Hello and goodbye

>>> Article.objects.get_count(Q(headline__startswith='Hello') | Q(headline__contains='bye'))
3

>>> Article.objects.get_values(Q(headline__startswith='Hello'), Q(headline__contains='bye'))
[{'headline': 'Hello and goodbye', 'pub_date': datetime.datetime(2005, 11, 29, 0, 0), 'id': 3}]

>>> Article.objects.get_in_bulk([1,2], Q(headline__startswith='Hello'))
{1: Hello}

"""

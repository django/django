"""
19. OR lookups

To perform an OR lookup, or a lookup that combines ANDs and ORs, use the
``complex`` keyword argument, and pass it an expression of clauses using the
variable ``django.core.meta.Q``.
"""

from django.core import meta

class Article(meta.Model):
    headline = meta.CharField(maxlength=50)
    pub_date = meta.DateTimeField()
    class META:
       ordering = ('pub_date',)

    def __repr__(self):
        return self.headline

API_TESTS = """
>>> from datetime import datetime
>>> from django.core.meta import Q

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

"""

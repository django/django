# coding: utf-8
from django.db import models
from django.conf import settings

try:
    sorted
except NameError:
    from django.utils.itercompat import sorted      # For Python 2.3

class Author(models.Model):
   name = models.CharField(max_length=100)
   age = models.IntegerField()
   friends = models.ManyToManyField('self', blank=True)

   def __unicode__(self):
      return self.name

class Publisher(models.Model):
   name = models.CharField(max_length=300)
   num_awards = models.IntegerField()

   def __unicode__(self):
      return self.name

class Book(models.Model):
   isbn = models.CharField(max_length=9)
   name = models.CharField(max_length=300)
   pages = models.IntegerField()
   rating = models.FloatField()
   price = models.DecimalField(decimal_places=2, max_digits=6)
   authors = models.ManyToManyField(Author)
   publisher = models.ForeignKey(Publisher)
   pubdate = models.DateField()

   class Meta:
       ordering = ('name',)

   def __unicode__(self):
      return self.name

class Store(models.Model):
   name = models.CharField(max_length=300)
   books = models.ManyToManyField(Book)
   original_opening = models.DateTimeField()
   friday_night_closing = models.TimeField()

   def __unicode__(self):
      return self.name

#Extra does not play well with values. Modify the tests if/when this is fixed.
__test__ = {'API_TESTS': """
>>> from django.core import management
>>> from django.db.models import get_app

# Reset the database representation of this app.
# This will return the database to a clean initial state.
>>> management.call_command('flush', verbosity=0, interactive=False)

>>> from django.db.models import Avg, Sum, Count, Max, Min, StdDev, Variance

# Ordering requests are ignored
>>> Author.objects.all().order_by('name').aggregate(Avg('age'))
{'age__avg': 37.4...}

# Implicit ordering is also ignored
>>> Book.objects.all().aggregate(Sum('pages'))
{'pages__sum': 3703}

# Baseline results
>>> Book.objects.all().aggregate(Sum('pages'), Avg('pages'))
{'pages__sum': 3703, 'pages__avg': 617.1...}

# Empty values query doesn't affect grouping or results
>>> Book.objects.all().values().aggregate(Sum('pages'), Avg('pages'))
{'pages__sum': 3703, 'pages__avg': 617.1...}

# Aggregate overrides extra selected column
>>> Book.objects.all().extra(select={'price_per_page' : 'price / pages'}).aggregate(Sum('pages'))
{'pages__sum': 3703}

# Annotations get combined with extra select clauses
>>> sorted(Book.objects.all().annotate(mean_auth_age=Avg('authors__age')).extra(select={'manufacture_cost' : 'price * .5'}).get(pk=2).__dict__.items())
[('id', 2), ('isbn', u'067232959'), ('manufacture_cost', ...11.545...), ('mean_auth_age', 45.0), ('name', u'Sams Teach Yourself Django in 24 Hours'), ('pages', 528), ('price', Decimal("23.09")), ('pubdate', datetime.date(2008, 3, 3)), ('publisher_id', 2), ('rating', 3.0)]

# Order of the annotate/extra in the query doesn't matter
>>> sorted(Book.objects.all().extra(select={'manufacture_cost' : 'price * .5'}).annotate(mean_auth_age=Avg('authors__age')).get(pk=2).__dict__.items())
[('id', 2), ('isbn', u'067232959'), ('manufacture_cost', ...11.545...), ('mean_auth_age', 45.0), ('name', u'Sams Teach Yourself Django in 24 Hours'), ('pages', 528), ('price', Decimal("23.09")), ('pubdate', datetime.date(2008, 3, 3)), ('publisher_id', 2), ('rating', 3.0)]

# Values queries can be combined with annotate and extra
>>> sorted(Book.objects.all().annotate(mean_auth_age=Avg('authors__age')).extra(select={'manufacture_cost' : 'price * .5'}).values().get(pk=2).items())
[('id', 2), ('isbn', u'067232959'), ('manufacture_cost', ...11.545...), ('mean_auth_age', 45.0), ('name', u'Sams Teach Yourself Django in 24 Hours'), ('pages', 528), ('price', Decimal("23.09")), ('pubdate', datetime.date(2008, 3, 3)), ('publisher_id', 2), ('rating', 3.0)]

# The order of the values, annotate and extra clauses doesn't matter
>>> sorted(Book.objects.all().values().annotate(mean_auth_age=Avg('authors__age')).extra(select={'manufacture_cost' : 'price * .5'}).get(pk=2).items())
[('id', 2), ('isbn', u'067232959'), ('manufacture_cost', ...11.545...), ('mean_auth_age', 45.0), ('name', u'Sams Teach Yourself Django in 24 Hours'), ('pages', 528), ('price', Decimal("23.09")), ('pubdate', datetime.date(2008, 3, 3)), ('publisher_id', 2), ('rating', 3.0)]

# A values query that selects specific columns reduces the output
>>> sorted(Book.objects.all().annotate(mean_auth_age=Avg('authors__age')).extra(select={'price_per_page' : 'price / pages'}).values('name').get(pk=1).items())
[('mean_auth_age', 34.5), ('name', u'The Definitive Guide to Django: Web Development Done Right')]

# The annotations are added to values output if values() precedes annotate()
>>> sorted(Book.objects.all().values('name').annotate(mean_auth_age=Avg('authors__age')).extra(select={'price_per_page' : 'price / pages'}).get(pk=1).items())
[('mean_auth_age', 34.5), ('name', u'The Definitive Guide to Django: Web Development Done Right')]

# Check that all of the objects are getting counted (allow_nulls) and that values respects the amount of objects
>>> len(Author.objects.all().annotate(Avg('friends__age')).values())
9

# Check that consecutive calls to annotate accumulate in the query
>>> Book.objects.values('price').annotate(oldest=Max('authors__age')).order_by('oldest', 'price').annotate(Max('publisher__num_awards'))
[{'price': Decimal("30..."), 'oldest': 35, 'publisher__num_awards__max': 3}, {'price': Decimal("29.69"), 'oldest': 37, 'publisher__num_awards__max': 7}, {'price': Decimal("23.09"), 'oldest': 45, 'publisher__num_awards__max': 1}, {'price': Decimal("75..."), 'oldest': 57, 'publisher__num_awards__max': 9}, {'price': Decimal("82.8..."), 'oldest': 57, 'publisher__num_awards__max': 7}]

# Aggregates can be composed over annotations.
# The return type is derived from the composed aggregate
>>> Book.objects.all().annotate(num_authors=Count('authors__id')).aggregate(Max('pages'), Max('price'), Sum('num_authors'), Avg('num_authors'))
{'num_authors__sum': 10, 'num_authors__avg': 1.66..., 'pages__max': 1132, 'price__max': Decimal("82.80")}

# Bad field requests in aggregates are caught and reported
>>> Book.objects.all().aggregate(num_authors=Count('foo'))
Traceback (most recent call last):
...
FieldError: Cannot resolve keyword 'foo' into field. Choices are: authors, id, isbn, name, pages, price, pubdate, publisher, rating, store

>>> Book.objects.all().annotate(num_authors=Count('foo'))
Traceback (most recent call last):
...
FieldError: Cannot resolve keyword 'foo' into field. Choices are: authors, id, isbn, name, pages, price, pubdate, publisher, rating, store

>>> Book.objects.all().annotate(num_authors=Count('authors__id')).aggregate(Max('foo'))
Traceback (most recent call last):
...
FieldError: Cannot resolve keyword 'foo' into field. Choices are: authors, id, isbn, name, pages, price, pubdate, publisher, rating, store, num_authors

# Old-style count aggregations can be mixed with new-style
>>> Book.objects.annotate(num_authors=Count('authors')).count()
6

# Non-ordinal, non-computed Aggregates over annotations correctly inherit
# the annotation's internal type if the annotation is ordinal or computed
>>> Book.objects.annotate(num_authors=Count('authors')).aggregate(Max('num_authors'))
{'num_authors__max': 3}

>>> Publisher.objects.annotate(avg_price=Avg('book__price')).aggregate(Max('avg_price'))
{'avg_price__max': 75.0...}

# Aliases are quoted to protected aliases that might be reserved names
>>> Book.objects.aggregate(number=Max('pages'), select=Max('pages'))
{'number': 1132, 'select': 1132}

# Regression for #10064: select_related() plays nice with aggregates
>>> Book.objects.select_related('publisher').annotate(num_authors=Count('authors')).values()[0]
{'rating': 4.0, 'isbn': u'013790395', 'name': u'Artificial Intelligence: A Modern Approach', 'pubdate': datetime.date(1995, 1, 15), 'price': Decimal("82.8..."), 'id': 5, 'num_authors': 2, 'publisher_id': 3, 'pages': 1132}

# Regression for #10010: exclude on an aggregate field is correctly negated
>>> len(Book.objects.annotate(num_authors=Count('authors')))
6
>>> len(Book.objects.annotate(num_authors=Count('authors')).filter(num_authors__gt=2))
1
>>> len(Book.objects.annotate(num_authors=Count('authors')).exclude(num_authors__gt=2))
5

>>> len(Book.objects.annotate(num_authors=Count('authors')).filter(num_authors__lt=3).exclude(num_authors__lt=2))
2
>>> len(Book.objects.annotate(num_authors=Count('authors')).exclude(num_authors__lt=2).filter(num_authors__lt=3))
2

# Regression for #10089: Check handling of empty result sets with aggregates
>>> Book.objects.filter(id__in=[]).count()
0

>>> Book.objects.filter(id__in=[]).aggregate(num_authors=Count('authors'), avg_authors=Avg('authors'), max_authors=Max('authors'), max_price=Max('price'), max_rating=Max('rating'))
{'max_authors': None, 'max_rating': None, 'num_authors': 0, 'avg_authors': None, 'max_price': None}

>>> Publisher.objects.filter(pk=5).annotate(num_authors=Count('book__authors'), avg_authors=Avg('book__authors'), max_authors=Max('book__authors'), max_price=Max('book__price'), max_rating=Max('book__rating')).values()
[{'max_authors': None, 'name': u"Jonno's House of Books", 'num_awards': 0, 'max_price': None, 'num_authors': 0, 'max_rating': None, 'id': 5, 'avg_authors': None}]

# Regression for #10113 - Fields mentioned in order_by() must be included in the GROUP BY.
# This only becomes a problem when the order_by introduces a new join.
>>> Book.objects.annotate(num_authors=Count('authors')).order_by('publisher__name')
[<Book: The Definitive Guide to Django: Web Development Done Right>, <Book: Practical Django Projects>, <Book: Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp>, <Book: Python Web Development with Django>, <Book: Artificial Intelligence: A Modern Approach>, <Book: Sams Teach Yourself Django in 24 Hours>]

"""
}

if settings.DATABASE_ENGINE != 'sqlite3':
    __test__['API_TESTS'] += """
# Stddev and Variance are not guaranteed to be available for SQLite.

>>> Book.objects.aggregate(StdDev('pages'))
{'pages__stddev': 311.46...}

>>> Book.objects.aggregate(StdDev('rating'))
{'rating__stddev': 0.60...}

>>> Book.objects.aggregate(StdDev('price'))
{'price__stddev': 24.16...}


>>> Book.objects.aggregate(StdDev('pages', sample=True))
{'pages__stddev': 341.19...}

>>> Book.objects.aggregate(StdDev('rating', sample=True))
{'rating__stddev': 0.66...}

>>> Book.objects.aggregate(StdDev('price', sample=True))
{'price__stddev': 26.46...}


>>> Book.objects.aggregate(Variance('pages'))
{'pages__variance': 97010.80...}

>>> Book.objects.aggregate(Variance('rating'))
{'rating__variance': 0.36...}

>>> Book.objects.aggregate(Variance('price'))
{'price__variance': 583.77...}


>>> Book.objects.aggregate(Variance('pages', sample=True))
{'pages__variance': 116412.96...}

>>> Book.objects.aggregate(Variance('rating', sample=True))
{'rating__variance': 0.44...}

>>> Book.objects.aggregate(Variance('price', sample=True))
{'price__variance': 700.53...}


"""


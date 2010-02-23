# coding: utf-8
from django.db import models

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
    name = models.CharField(max_length=255)
    num_awards = models.IntegerField()

    def __unicode__(self):
        return self.name

class Book(models.Model):
    isbn = models.CharField(max_length=9)
    name = models.CharField(max_length=255)
    pages = models.IntegerField()
    rating = models.FloatField()
    price = models.DecimalField(decimal_places=2, max_digits=6)
    authors = models.ManyToManyField(Author)
    contact = models.ForeignKey(Author, related_name='book_contact_set')
    publisher = models.ForeignKey(Publisher)
    pubdate = models.DateField()

    def __unicode__(self):
        return self.name

class Store(models.Model):
    name = models.CharField(max_length=255)
    books = models.ManyToManyField(Book)
    original_opening = models.DateTimeField()
    friday_night_closing = models.TimeField()

    def __unicode__(self):
        return self.name

# Tests on 'aggregate'
# Different backends and numbers.
__test__ = {'API_TESTS': """
>>> from django.core import management
>>> try:
...     from decimal import Decimal
... except:
...     from django.utils._decimal import Decimal
>>> from datetime import date

# Reset the database representation of this app.
# This will return the database to a clean initial state.
>>> management.call_command('flush', verbosity=0, interactive=False)

# Empty Call - request nothing, get nothing.
>>> Author.objects.all().aggregate()
{}

>>> from django.db.models import Avg, Sum, Count, Max, Min

# Single model aggregation
#

# Single aggregate
# Average age of Authors
>>> Author.objects.all().aggregate(Avg('age'))
{'age__avg': 37.4...}

# Multiple aggregates
# Average and Sum of Author ages
>>> Author.objects.all().aggregate(Sum('age'), Avg('age'))
{'age__sum': 337, 'age__avg': 37.4...}

# Aggreates interact with filters, and only
# generate aggregate values for the filtered values
# Sum of the age of those older than 29 years old
>>> Author.objects.all().filter(age__gt=29).aggregate(Sum('age'))
{'age__sum': 254}

# Depth-1 Joins
#

# On Relationships with self
# Average age of the friends of each author
>>> Author.objects.all().aggregate(Avg('friends__age'))
{'friends__age__avg': 34.07...}

# On ManyToMany Relationships
#

# Forward
# Average age of the Authors of Books with a rating of less than 4.5
>>> Book.objects.all().filter(rating__lt=4.5).aggregate(Avg('authors__age'))
{'authors__age__avg': 38.2...}

# Backward
# Average rating of the Books whose Author's name contains the letter 'a'
>>> Author.objects.all().filter(name__contains='a').aggregate(Avg('book__rating'))
{'book__rating__avg': 4.0}

# On OneToMany Relationships
#

# Forward
# Sum of the number of awards of each Book's Publisher
>>> Book.objects.all().aggregate(Sum('publisher__num_awards'))
{'publisher__num_awards__sum': 30}

# Backward
# Sum of the price of every Book that has a Publisher
>>> Publisher.objects.all().aggregate(Sum('book__price'))
{'book__price__sum': Decimal("270.27")}

# Multiple Joins
#

# Forward
>>> Store.objects.all().aggregate(Max('books__authors__age'))
{'books__authors__age__max': 57}

# Backward
# Note that the very long default alias may be truncated
>>> Author.objects.all().aggregate(Min('book__publisher__num_awards'))
{'book__publisher__num_award...': 1}

# Aggregate outputs can also be aliased.

# Average amazon.com Book rating
>>> Store.objects.filter(name='Amazon.com').aggregate(amazon_mean=Avg('books__rating'))
{'amazon_mean': 4.08...}

# Tests on annotate()

# An empty annotate call does nothing but return the same QuerySet
>>> Book.objects.all().annotate().order_by('pk')
[<Book: The Definitive Guide to Django: Web Development Done Right>, <Book: Sams Teach Yourself Django in 24 Hours>, <Book: Practical Django Projects>, <Book: Python Web Development with Django>, <Book: Artificial Intelligence: A Modern Approach>, <Book: Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp>]

# Annotate inserts the alias into the model object with the aggregated result
>>> books = Book.objects.all().annotate(mean_age=Avg('authors__age'))
>>> books.get(pk=1).name
u'The Definitive Guide to Django: Web Development Done Right'

>>> books.get(pk=1).mean_age
34.5

# On ManyToMany Relationships

# Forward
# Average age of the Authors of each book with a rating less than 4.5
>>> books = Book.objects.all().filter(rating__lt=4.5).annotate(Avg('authors__age'))
>>> sorted([(b.name, b.authors__age__avg) for b in books])
[(u'Artificial Intelligence: A Modern Approach', 51.5), (u'Practical Django Projects', 29.0), (u'Python Web Development with Django', 30.3...), (u'Sams Teach Yourself Django in 24 Hours', 45.0)]

# Count the number of authors of each book
>>> books = Book.objects.annotate(num_authors=Count('authors'))
>>> sorted([(b.name, b.num_authors) for b in books])
[(u'Artificial Intelligence: A Modern Approach', 2), (u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp', 1), (u'Practical Django Projects', 1), (u'Python Web Development with Django', 3), (u'Sams Teach Yourself Django in 24 Hours', 1), (u'The Definitive Guide to Django: Web Development Done Right', 2)]

# Backward
# Average rating of the Books whose Author's names contains the letter 'a'
>>> authors = Author.objects.all().filter(name__contains='a').annotate(Avg('book__rating'))
>>> sorted([(a.name, a.book__rating__avg) for a in authors])
[(u'Adrian Holovaty', 4.5), (u'Brad Dayley', 3.0), (u'Jacob Kaplan-Moss', 4.5), (u'James Bennett', 4.0), (u'Paul Bissex', 4.0), (u'Stuart Russell', 4.0)]

# Count the number of books written by each author
>>> authors = Author.objects.annotate(num_books=Count('book'))
>>> sorted([(a.name, a.num_books) for a in authors])
[(u'Adrian Holovaty', 1), (u'Brad Dayley', 1), (u'Jacob Kaplan-Moss', 1), (u'James Bennett', 1), (u'Jeffrey Forcier', 1), (u'Paul Bissex', 1), (u'Peter Norvig', 2), (u'Stuart Russell', 1), (u'Wesley J. Chun', 1)]

# On OneToMany Relationships

# Forward
# Annotate each book with the number of awards of each Book's Publisher
>>> books = Book.objects.all().annotate(Sum('publisher__num_awards'))
>>> sorted([(b.name, b.publisher__num_awards__sum) for b in books])
[(u'Artificial Intelligence: A Modern Approach', 7), (u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp', 9), (u'Practical Django Projects', 3), (u'Python Web Development with Django', 7), (u'Sams Teach Yourself Django in 24 Hours', 1), (u'The Definitive Guide to Django: Web Development Done Right', 3)]

# Backward
# Annotate each publisher with the sum of the price of all books sold
>>> publishers = Publisher.objects.all().annotate(Sum('book__price'))
>>> sorted([(p.name, p.book__price__sum) for p in publishers])
[(u'Apress', Decimal("59.69")), (u"Jonno's House of Books", None), (u'Morgan Kaufmann', Decimal("75.00")), (u'Prentice Hall', Decimal("112.49")), (u'Sams', Decimal("23.09"))]

# Calls to values() are not commutative over annotate().

# Calling values on a queryset that has annotations returns the output
# as a dictionary
>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values()
[{'rating': 4.5, 'isbn': u'159059725', 'name': u'The Definitive Guide to Django: Web Development Done Right', 'pubdate': datetime.date(2007, 12, 6), 'price': Decimal("30..."), 'contact_id': 1, 'id': 1, 'publisher_id': 1, 'pages': 447, 'mean_age': 34.5}]

>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values('pk', 'isbn', 'mean_age')
[{'pk': 1, 'isbn': u'159059725', 'mean_age': 34.5}]

# Calling values() with parameters reduces the output
>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values('name')
[{'name': u'The Definitive Guide to Django: Web Development Done Right'}]

# An empty values() call before annotating has the same effect as an
# empty values() call after annotating
>>> Book.objects.filter(pk=1).values().annotate(mean_age=Avg('authors__age'))
[{'rating': 4.5, 'isbn': u'159059725', 'name': u'The Definitive Guide to Django: Web Development Done Right', 'pubdate': datetime.date(2007, 12, 6), 'price': Decimal("30..."), 'contact_id': 1, 'id': 1, 'publisher_id': 1, 'pages': 447, 'mean_age': 34.5}]

# Calling annotate() on a ValuesQuerySet annotates over the groups of
# fields to be selected by the ValuesQuerySet.

# Note that an extra parameter is added to each dictionary. This
# parameter is a queryset representing the objects that have been
# grouped to generate the annotation

>>> Book.objects.all().values('rating').annotate(n_authors=Count('authors__id'), mean_age=Avg('authors__age')).order_by('rating')
[{'rating': 3.0, 'n_authors': 1, 'mean_age': 45.0}, {'rating': 4.0, 'n_authors': 6, 'mean_age': 37.1...}, {'rating': 4.5, 'n_authors': 2, 'mean_age': 34.5}, {'rating': 5.0, 'n_authors': 1, 'mean_age': 57.0}]

# If a join doesn't match any objects, an aggregate returns None
>>> authors = Author.objects.all().annotate(Avg('friends__age')).order_by('id')
>>> len(authors)
9
>>> sorted([(a.name, a.friends__age__avg) for a in authors])
[(u'Adrian Holovaty', 32.0), (u'Brad Dayley', None), (u'Jacob Kaplan-Moss', 29.5), (u'James Bennett', 34.0), (u'Jeffrey Forcier', 27.0), (u'Paul Bissex', 31.0), (u'Peter Norvig', 46.0), (u'Stuart Russell', 57.0), (u'Wesley J. Chun', 33.6...)]


# The Count aggregation function allows an extra parameter: distinct.
# This restricts the count results to unique items
>>> Book.objects.all().aggregate(Count('rating'))
{'rating__count': 6}

>>> Book.objects.all().aggregate(Count('rating', distinct=True))
{'rating__count': 4}

# Retreiving the grouped objects

# When using Count you can also omit the primary key and refer only to
# the related field name if you want to count all the related objects
# and not a specific column
>>> explicit = list(Author.objects.annotate(Count('book__id')))
>>> implicit = list(Author.objects.annotate(Count('book')))
>>> explicit == implicit
True

# Ordering is allowed on aggregates
>>> Book.objects.values('rating').annotate(oldest=Max('authors__age')).order_by('oldest', 'rating')
[{'rating': 4.5, 'oldest': 35}, {'rating': 3.0, 'oldest': 45}, {'rating': 4.0, 'oldest': 57}, {'rating': 5.0, 'oldest': 57}]

>>> Book.objects.values('rating').annotate(oldest=Max('authors__age')).order_by('-oldest', '-rating')
[{'rating': 5.0, 'oldest': 57}, {'rating': 4.0, 'oldest': 57}, {'rating': 3.0, 'oldest': 45}, {'rating': 4.5, 'oldest': 35}]

# It is possible to aggregate over anotated values
>>> Book.objects.all().annotate(num_authors=Count('authors__id')).aggregate(Avg('num_authors'))
{'num_authors__avg': 1.66...}

# You can filter the results based on the aggregation alias.

# Lets add a publisher to test the different possibilities for filtering
>>> p = Publisher(name='Expensive Publisher', num_awards=0)
>>> p.save()
>>> Book(name='ExpensiveBook1', pages=1, isbn='111', rating=3.5, price=Decimal("1000"), publisher=p, contact_id=1, pubdate=date(2008,12,1)).save()
>>> Book(name='ExpensiveBook2', pages=1, isbn='222', rating=4.0, price=Decimal("1000"), publisher=p, contact_id=1, pubdate=date(2008,12,2)).save()
>>> Book(name='ExpensiveBook3', pages=1, isbn='333', rating=4.5, price=Decimal("35"), publisher=p, contact_id=1, pubdate=date(2008,12,3)).save()

# Publishers that have:

# (i) more than one book
>>> Publisher.objects.annotate(num_books=Count('book__id')).filter(num_books__gt=1).order_by('pk')
[<Publisher: Apress>, <Publisher: Prentice Hall>, <Publisher: Expensive Publisher>]

# (ii) a book that cost less than 40
>>> Publisher.objects.filter(book__price__lt=Decimal("40.0")).order_by('pk')
[<Publisher: Apress>, <Publisher: Apress>, <Publisher: Sams>, <Publisher: Prentice Hall>, <Publisher: Expensive Publisher>]

# (iii) more than one book and (at least) a book that cost less than 40
>>> Publisher.objects.annotate(num_books=Count('book__id')).filter(num_books__gt=1, book__price__lt=Decimal("40.0")).order_by('pk')
[<Publisher: Apress>, <Publisher: Prentice Hall>, <Publisher: Expensive Publisher>]

# (iv) more than one book that costs less than $40
>>> Publisher.objects.filter(book__price__lt=Decimal("40.0")).annotate(num_books=Count('book__id')).filter(num_books__gt=1).order_by('pk')
[<Publisher: Apress>]

# Now a bit of testing on the different lookup types
#

>>> Publisher.objects.annotate(num_books=Count('book')).filter(num_books__range=[1, 3]).order_by('pk')
[<Publisher: Apress>, <Publisher: Sams>, <Publisher: Prentice Hall>, <Publisher: Morgan Kaufmann>, <Publisher: Expensive Publisher>]

>>> Publisher.objects.annotate(num_books=Count('book')).filter(num_books__range=[1, 2]).order_by('pk')
[<Publisher: Apress>, <Publisher: Sams>, <Publisher: Prentice Hall>, <Publisher: Morgan Kaufmann>]

>>> Publisher.objects.annotate(num_books=Count('book')).filter(num_books__in=[1, 3]).order_by('pk')
[<Publisher: Sams>, <Publisher: Morgan Kaufmann>, <Publisher: Expensive Publisher>]

>>> Publisher.objects.annotate(num_books=Count('book')).filter(num_books__isnull=True)
[]

>>> p.delete()

# Does Author X have any friends? (or better, how many friends does author X have)
>> Author.objects.filter(pk=1).aggregate(Count('friends__id'))
{'friends__id__count': 2.0}

# Give me a list of all Books with more than 1 authors
>>> Book.objects.all().annotate(num_authors=Count('authors__name')).filter(num_authors__ge=2).order_by('pk')
[<Book: The Definitive Guide to Django: Web Development Done Right>, <Book: Artificial Intelligence: A Modern Approach>]

# Give me a list of all Authors that have no friends
>>> Author.objects.all().annotate(num_friends=Count('friends__id', distinct=True)).filter(num_friends=0).order_by('pk')
[<Author: Brad Dayley>]

# Give me a list of all publishers that have published more than 1 books
>>> Publisher.objects.all().annotate(num_books=Count('book__id')).filter(num_books__gt=1).order_by('pk')
[<Publisher: Apress>, <Publisher: Prentice Hall>]

# Give me a list of all publishers that have published more than 1 books that cost less than 40
>>> Publisher.objects.all().filter(book__price__lt=Decimal("40.0")).annotate(num_books=Count('book__id')).filter(num_books__gt=1)
[<Publisher: Apress>]

# Give me a list of all Books that were written by X and one other author.
>>> Book.objects.all().annotate(num_authors=Count('authors__id')).filter(authors__name__contains='Norvig', num_authors__gt=1)
[<Book: Artificial Intelligence: A Modern Approach>]

# Give me the average rating of all Books that were written by X and one other author.
#(Aggregate over objects discovered using membership of the m2m set)

# Adding an existing author to another book to test it the right way
>>> a = Author.objects.get(name__contains='Norvig')
>>> b = Book.objects.get(name__contains='Done Right')
>>> b.authors.add(a)
>>> b.save()

# This should do it
>>> Book.objects.all().annotate(num_authors=Count('authors__id')).filter(authors__name__contains='Norvig', num_authors__gt=1).aggregate(Avg('rating'))
{'rating__avg': 4.25}
>>> b.authors.remove(a)

# Give me a list of all Authors that have published a book with at least one other person
# (Filters over a count generated on a related object)
#
# Cheating: [a for a in Author.objects.all().annotate(num_coleagues=Count('book__authors__id'), num_books=Count('book__id', distinct=True)) if a.num_coleagues - a.num_books > 0]
# F-Syntax is required. Will be fixed after F objects are available

# Aggregates also work on dates, times and datetimes
>>> Publisher.objects.annotate(earliest_book=Min('book__pubdate')).exclude(earliest_book=None).order_by('earliest_book').values()
[{'earliest_book': datetime.date(1991, 10, 15), 'num_awards': 9, 'id': 4, 'name': u'Morgan Kaufmann'}, {'earliest_book': datetime.date(1995, 1, 15), 'num_awards': 7, 'id': 3, 'name': u'Prentice Hall'}, {'earliest_book': datetime.date(2007, 12, 6), 'num_awards': 3, 'id': 1, 'name': u'Apress'}, {'earliest_book': datetime.date(2008, 3, 3), 'num_awards': 1, 'id': 2, 'name': u'Sams'}]

>>> Store.objects.aggregate(Max('friday_night_closing'), Min("original_opening"))
{'friday_night_closing__max': datetime.time(23, 59, 59), 'original_opening__min': datetime.datetime(1945, 4, 25, 16, 24, 14)}

# values_list() can also be used

>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values_list('pk', 'isbn', 'mean_age')
[(1, u'159059725', 34.5)]

>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values_list('isbn')
[(u'159059725',)]

>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values_list('mean_age')
[(34.5,)]

>>> Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values_list('mean_age', flat=True)
[34.5]

>>> qs = Book.objects.values_list('price').annotate(count=Count('price')).order_by('-count', 'price')
>>> list(qs) == [(Decimal('29.69'), 2), (Decimal('23.09'), 1), (Decimal('30'), 1), (Decimal('75'), 1), (Decimal('82.8'), 1)]
True

"""}

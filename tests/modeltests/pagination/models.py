"""
30. Object pagination

Django provides a framework for paginating a list of objects in a few lines
of code. This is often useful for dividing search results or long lists of
objects into easily readable pages.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS':"""
# Prepare a list of objects for pagination.
>>> from datetime import datetime
>>> for x in range(1, 10):
...     a = Article(headline='Article %s' % x, pub_date=datetime(2005, 7, 29))
...     a.save()

##################
# Paginator/Page #
##################

>>> from django.core.paginator import Paginator
>>> paginator = Paginator(Article.objects.all(), 5)
>>> paginator.count
9
>>> paginator.num_pages
2
>>> paginator.page_range
[1, 2]

# Get the first page.
>>> p = paginator.page(1)
>>> p
<Page 1 of 2>
>>> p.object_list
[<Article: Article 1>, <Article: Article 2>, <Article: Article 3>, <Article: Article 4>, <Article: Article 5>]
>>> p.has_next()
True
>>> p.has_previous()
False
>>> p.has_other_pages()
True
>>> p.next_page_number()
2
>>> p.previous_page_number()
0
>>> p.start_index()
1
>>> p.end_index()
5

# Get the second page.
>>> p = paginator.page(2)
>>> p
<Page 2 of 2>
>>> p.object_list
[<Article: Article 6>, <Article: Article 7>, <Article: Article 8>, <Article: Article 9>]
>>> p.has_next()
False
>>> p.has_previous()
True
>>> p.has_other_pages()
True
>>> p.next_page_number()
3
>>> p.previous_page_number()
1
>>> p.start_index()
6
>>> p.end_index()
9

# Empty pages raise EmptyPage.
>>> paginator.page(0)
Traceback (most recent call last):
...
EmptyPage: ...
>>> paginator.page(3)
Traceback (most recent call last):
...
EmptyPage: ...

# Empty paginators with allow_empty_first_page=True.
>>> paginator = Paginator(Article.objects.filter(id=0), 5, allow_empty_first_page=True)
>>> paginator.count
0
>>> paginator.num_pages
1
>>> paginator.page_range
[1]

# Empty paginators with allow_empty_first_page=False.
>>> paginator = Paginator(Article.objects.filter(id=0), 5, allow_empty_first_page=False)
>>> paginator.count
0
>>> paginator.num_pages
0
>>> paginator.page_range
[]

# Paginators work with regular lists/tuples, too -- not just with QuerySets.
>>> paginator = Paginator([1, 2, 3, 4, 5, 6, 7, 8, 9], 5)
>>> paginator.count
9
>>> paginator.num_pages
2
>>> paginator.page_range
[1, 2]

# Get the first page.
>>> p = paginator.page(1)
>>> p
<Page 1 of 2>
>>> p.object_list
[1, 2, 3, 4, 5]
>>> p.has_next()
True
>>> p.has_previous()
False
>>> p.has_other_pages()
True
>>> p.next_page_number()
2
>>> p.previous_page_number()
0
>>> p.start_index()
1
>>> p.end_index()
5

# Paginator can be passed other objects with a count() method.
>>> class CountContainer:
...     def count(self):
...         return 42
>>> paginator = Paginator(CountContainer(), 10)
>>> paginator.count
42
>>> paginator.num_pages
5
>>> paginator.page_range
[1, 2, 3, 4, 5]

# Paginator can be passed other objects that implement __len__.
>>> class LenContainer:
...     def __len__(self):
...         return 42
>>> paginator = Paginator(LenContainer(), 10)
>>> paginator.count
42
>>> paginator.num_pages
5
>>> paginator.page_range
[1, 2, 3, 4, 5]


##################
# Orphan support #
##################

# Add a few more records to test out the orphans feature.
>>> for x in range(10, 13):
...     Article(headline="Article %s" % x, pub_date=datetime(2006, 10, 6)).save()

# With orphans set to 3 and 10 items per page, we should get all 12 items on a single page.
>>> paginator = Paginator(Article.objects.all(), 10, orphans=3)
>>> paginator.num_pages
1

# With orphans only set to 1, we should get two pages.
>>> paginator = Paginator(Article.objects.all(), 10, orphans=1)
>>> paginator.num_pages
2
"""}

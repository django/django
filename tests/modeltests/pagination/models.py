"""
20. Object Pagination

Django provides a framework for paginating a list of objects in a few.  
This is often useful for dividing search results or long lists of objects
in to easily readable pages.


"""
from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100, default='Default headline')
    pub_date = models.DateTimeField()
    
    def __repr__(self):
        return self.headline 
        
API_TESTS = """
# prepare a list of objects for pagination
>>> from datetime import datetime
>>> for x in range(1, 10):
...     a = Article(headline='Article %s' % x, pub_date=datetime(2005, 7, 29))
...     a.save()

# create a basic paginator, 5 articles per page
>>> from django.core.paginator import ObjectPaginator, InvalidPage
>>> paginator = ObjectPaginator(Article.objects.all(), 5)

# the paginator knows how many hits and pages it contains
>>> paginator.hits
9

>>> paginator.pages
2

# get the first page (zero-based)    
>>> paginator.get_page(0)  
[Article 1, Article 2, Article 3, Article 4, Article 5]

# get the second page
>>> paginator.get_page(1)
[Article 6, Article 7, Article 8, Article 9]

# does the first page have a next or previous page?
>>> paginator.has_next_page(0)
True
                                                
>>> paginator.has_previous_page(0)
False

# check the second page
>>> paginator.has_next_page(1)
False

>>> paginator.has_previous_page(1)
True
 
"""

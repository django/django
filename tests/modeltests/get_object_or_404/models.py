"""
34. DB-API Shortcuts

get_object_or_404 is a shortcut function to be used in view functions for
performing a get() lookup and raising a Http404 exception if a DoesNotExist
exception was rasied during the get() call.

get_list_or_404 is a shortcut function to be used in view functions for
performing a filter() lookup and raising a Http404 exception if a DoesNotExist
exception was rasied during the filter() call.
"""

from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, get_list_or_404

class Author(models.Model):
    name = models.CharField(maxlength=50)
    
    def __str__(self):
        return self.name

class ArticleManager(models.Manager):
    def get_query_set(self):
        return super(ArticleManager, self).get_query_set().filter(authors__name__icontains='sir')

class Article(models.Model):
    authors = models.ManyToManyField(Author)
    title = models.CharField(maxlength=50)
    objects = models.Manager()
    by_a_sir = ArticleManager()
    
    def __str__(self):
        return self.title

__test__ = {'API_TESTS':"""
# Create some Authors.
>>> a = Author.objects.create(name="Brave Sir Robin")
>>> a.save()
>>> a2 = Author.objects.create(name="Patsy")
>>> a2.save()

# No Articles yet, so we should get a Http404 error.
>>> get_object_or_404(Article, title="Foo")
Traceback (most recent call last):
...
Http404: No Article matches the given query.

# Create an Article.
>>> article = Article.objects.create(title="Run away!")
>>> article.authors = [a, a2]
>>> article.save()

# get_object_or_404 can be passed a Model to query.
>>> get_object_or_404(Article, title__contains="Run")
<Article: Run away!>

# We can also use the the Article manager through an Author object.
>>> get_object_or_404(a.article_set, title__contains="Run")
<Article: Run away!>

# No articles containing "Camelot".  This should raise a Http404 error.
>>> get_object_or_404(a.article_set, title__contains="Camelot")
Traceback (most recent call last):
...
Http404: No Article matches the given query.

# Custom managers can be used too.
>>> get_object_or_404(Article.by_a_sir, title="Run away!")
<Article: Run away!>

# get_list_or_404 can be used to get lists of objects
>>> get_list_or_404(a.article_set, title__icontains='Run')
[<Article: Run away!>]

# Http404 is returned if the list is empty
>>> get_list_or_404(a.article_set, title__icontains='Shrubbery')
Traceback (most recent call last):
...
Http404: No Article matches the given query.

# Custom managers can be used too.
>>> get_list_or_404(Article.by_a_sir, title__icontains="Run")
[<Article: Run away!>]

"""}

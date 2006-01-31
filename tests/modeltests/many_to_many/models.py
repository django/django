"""
5. Many-to-many relationships

To define a many-to-many relationship, use ManyToManyField().

In this example, an article can be published in multiple publications,
and a publication has multiple articles.
"""

from django.db import models

class Publication(models.Model):
    title = models.CharField(maxlength=30)

    def __repr__(self):
        return self.title

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    publications = models.ManyToManyField(Publication)

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a couple of Publications.
>>> p1 = Publication(id=None, title='The Python Journal')
>>> p1.save()
>>> p2 = Publication(id=None, title='Science News')
>>> p2.save()
>>> p3 = Publication(id=None, title='Science Weekly')
>>> p3.save()

# Create an Article.
>>> a1 = Article(id=None, headline='Django lets you build Web apps easily')
>>> a1.save()

# Associate the Article with one Publication. set_publications() returns a
# boolean, representing whether any records were added or deleted.
>>> a1.set_publications([p1.id])
True

# If we set it again, it'll return False, because the list of Publications
# hasn't changed.
>>> a1.set_publications([p1.id])
False

# Create another Article, and set it to appear in both Publications.
>>> a2 = Article(id=None, headline='NASA uses Python')
>>> a2.save()
>>> a2.set_publications([p1.id, p2.id])
True
>>> a2.set_publications([p1.id])
True
>>> a2.set_publications([p1.id, p2.id, p3.id])
True

# Article objects have access to their related Publication objects.
>>> a1.publication_set.all()
[The Python Journal]
>>> a2.publication_set.all()
[The Python Journal, Science News, Science Weekly]

# Publication objects have access to their related Article objects.
>>> p2.article_set.all()
[NASA uses Python]
>>> p1.article_set.order_by('headline')
[Django lets you build Web apps easily, NASA uses Python]

# We can perform kwarg queries across m2m relationships
>>> Article.objects.filter(publications__id__exact=1)
[Django lets you build Web apps easily, NASA uses Python]
>>> Article.objects.filter(publications__pk=1)
[Django lets you build Web apps easily, NASA uses Python]

>>> Article.objects.filter(publications__title__startswith="Science")
[NASA uses Python, NASA uses Python]

>>> Article.objects.filter(publications__title__startswith="Science").distinct()
[NASA uses Python]

# Reverse m2m queries (i.e., start at the table that doesn't have a ManyToManyField)
>>> Publication.objects.filter(id__exact=1)
[The Python Journal]
>>> Publication.objects.filter(pk=1)
[The Python Journal]

>>> Publication.objects.filter(article__headline__startswith="NASA")
[The Python Journal, Science News, Science Weekly]

>>> Publication.objects.filter(article__id__exact=1)
[The Python Journal]

>>> Publication.objects.filter(article__pk=1)
[The Python Journal]

# If we delete a Publication, its Articles won't be able to access it.
>>> p1.delete()
>>> Publication.objects.all()
[Science News, Science Weekly]
>>> a1 = Article.objects.get(pk=1)
>>> a1.publication_set.all()
[]

# If we delete an Article, its Publications won't be able to access it.
>>> a2.delete()
>>> Article.objects.all()
[Django lets you build Web apps easily]
>>> p1.article_set.order_by('headline')
[Django lets you build Web apps easily]
"""

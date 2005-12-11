"""
5. Many-to-many relationships

To define a many-to-many relationship, use ManyToManyField().

In this example, an article can be published in multiple publications,
and a publication has multiple articles.
"""

from django.core import meta

class Publication(meta.Model):
    title = meta.CharField(maxlength=30)

    def __repr__(self):
        return self.title

class Article(meta.Model):
    headline = meta.CharField(maxlength=100)
    publications = meta.ManyToManyField(Publication)

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a couple of Publications.
>>> p1 = Publication(id=None, title='The Python Journal')
>>> p1.save()
>>> p2 = Publication(id=None, title='Science News')
>>> p2.save()

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
>>> a2.set_publications([p1.id, p2.id])
True

# Article objects have access to their related Publication objects.
>>> a1.get_publication_list()
[The Python Journal]
>>> a2.get_publication_list()
[The Python Journal, Science News]

# Publication objects have access to their related Article objects.
>>> p2.get_article_list()
[NASA uses Python]
>>> p1.get_article_list(order_by=['headline'])
[Django lets you build Web apps easily, NASA uses Python]

# If we delete a Publication, its Articles won't be able to access it.
>>> p1.delete()
>>> publications.get_list()
[Science News]
>>> a1 = articles.get_object(pk=1)
>>> a1.get_publication_list()
[]

# If we delete an Article, its Publications won't be able to access it.
>>> a2.delete()
>>> articles.get_list()
[Django lets you build Web apps easily]
>>> p1.get_article_list(order_by=['headline'])
[Django lets you build Web apps easily]
"""

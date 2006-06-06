"""
20. Multiple many-to-many relationships between the same two tables

In this example, an Article can have many Categories (as "primary") and many
Categories (as "secondary").

Set ``related_name`` to designate what the reverse relationship is called.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    class Meta:
       ordering = ('name',)

    def __str__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateTimeField()
    primary_categories = models.ManyToManyField(Category, related_name='primary_article_set')
    secondary_categories = models.ManyToManyField(Category, related_name='secondary_article_set')
    class Meta:
       ordering = ('pub_date',)

    def __str__(self):
        return self.headline

API_TESTS = """
>>> from datetime import datetime

>>> c1 = Category(name='Sports')
>>> c1.save()
>>> c2 = Category(name='News')
>>> c2.save()
>>> c3 = Category(name='Crime')
>>> c3.save()
>>> c4 = Category(name='Life')
>>> c4.save()

>>> a1 = Article(headline='Area man steals', pub_date=datetime(2005, 11, 27))
>>> a1.save()
>>> a1.primary_categories.add(c2, c3)
>>> a1.secondary_categories.add(c4)

>>> a2 = Article(headline='Area man runs', pub_date=datetime(2005, 11, 28))
>>> a2.save()
>>> a2.primary_categories.add(c1, c2)
>>> a2.secondary_categories.add(c4)

>>> a1.primary_categories.all()
[<Category: Crime>, <Category: News>]

>>> a2.primary_categories.all()
[<Category: News>, <Category: Sports>]

>>> a1.secondary_categories.all()
[<Category: Life>]


>>> c1.primary_article_set.all()
[<Article: Area man runs>]
>>> c1.secondary_article_set.all()
[]
>>> c2.primary_article_set.all()
[<Article: Area man steals>, <Article: Area man runs>]
>>> c2.secondary_article_set.all()
[]
>>> c3.primary_article_set.all()
[<Article: Area man steals>]
>>> c3.secondary_article_set.all()
[]
>>> c4.primary_article_set.all()
[]
>>> c4.secondary_article_set.all()
[<Article: Area man steals>, <Article: Area man runs>]
"""

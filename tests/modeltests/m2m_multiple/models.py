"""
20. Multiple many-to-many relationships between the same two tables

In this example, an Article can have many Categories (as "primary") and many
Categories (as "secondary").

Set ``related_name`` to designate what the reverse relationship is called.

Set ``singular`` to designate what the category object is called. This is
required if a model has multiple ``ManyToManyFields`` to the same object.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    class Meta:
       ordering = ('name',)

    def __repr__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateTimeField()
    primary_categories = models.ManyToManyField(Category,
        singular='primary_category', related_name='primary_article')
    secondary_categories = models.ManyToManyField(Category,
        singular='secondary_category', related_name='secondary_article')
    class Meta:
       ordering = ('pub_date',)

    def __repr__(self):
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
>>> a1.set_primary_categories([c2.id, c3.id])
True
>>> a1.set_secondary_categories([c4.id])
True

>>> a2 = Article(headline='Area man runs', pub_date=datetime(2005, 11, 28))
>>> a2.save()
>>> a2.set_primary_categories([c1.id, c2.id])
True
>>> a2.set_secondary_categories([c4.id])
True

# The "primary_category" here comes from the "singular" parameter. If we hadn't
# specified the "singular" parameter, Django would just use "category", which
# would cause a conflict because the "primary_categories" and
# "secondary_categories" fields both relate to Category.
>>> a1.primary_category_set.all()
[Crime, News]

# Ditto for the "primary_category" here.
>>> a2.primary_category_set.all()
[News, Sports]

# Ditto for the "secondary_category" here.
>>> a1.secondary_category_set.all()
[Life]


>>> c1.primary_article_set.all()
[Area man runs]
>>> c1.secondary_article_set.all()
[]
>>> c2.primary_article_set.all()
[Area man steals, Area man runs]
>>> c2.secondary_article_set.all()
[]
>>> c3.primary_article_set.all()
[Area man steals]
>>> c3.secondary_article_set.all()
[]
>>> c4.primary_article_set.all()
[]
>>> c4.secondary_article_set.all()
[Area man steals, Area man runs]
"""

"""
1. Bare-bones model

This is a basic model with only two non-primary-key fields.
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100, default='Default headline')
    pub_date = models.DateTimeField()

API_TESTS = """
# No articles are in the system yet.
>>> Article.objects.get_list()
[]

# Create an Article.
>>> from datetime import datetime
>>> a = Article(id=None, headline='Area man programs in Python',
...     pub_date=datetime(2005, 7, 28))

# Save it into the database. You have to call save() explicitly.
>>> a.save()

# Now it has an ID. Note it's a long integer, as designated by the trailing "L".
>>> a.id
1L

# Access database columns via Python attributes.
>>> a.headline
'Area man programs in Python'
>>> a.pub_date
datetime.datetime(2005, 7, 28, 0, 0)

# Change values by changing the attributes, then calling save().
>>> a.headline = 'Area woman programs in Python'
>>> a.save()

# get_list() displays all the articles in the database. Note that the article
# is represented by "<Article object>", because we haven't given the Article
# model a __repr__() method.
>>> Article.objects.get_list()
[<Article object>]

# Django provides a rich database lookup API that's entirely driven by
# keyword arguments.
>>> Article.objects.get_object(id__exact=1)
<Article object>
>>> Article.objects.get_object(headline__startswith='Area woman')
<Article object>
>>> Article.objects.get_object(pub_date__year=2005)
<Article object>
>>> Article.objects.get_object(pub_date__year=2005, pub_date__month=7)
<Article object>
>>> Article.objects.get_object(pub_date__year=2005, pub_date__month=7, pub_date__day=28)
<Article object>

>>> Article.objects.get_list(pub_date__year=2005)
[<Article object>]
>>> Article.objects.get_list(pub_date__year=2004)
[]
>>> Article.objects.get_list(pub_date__year=2005, pub_date__month=7)
[<Article object>]

# Django raises an ArticleDoesNotExist exception for get_object()
>>> Article.objects.get_object(id__exact=2)
Traceback (most recent call last):
    ...
DoesNotExist: Article does not exist for {'id__exact': 2}

>>> Article.objects.get_object(pub_date__year=2005, pub_date__month=8)
Traceback (most recent call last):
    ...
DoesNotExist: Article does not exist for ...

# Lookup by a primary key is the most common case, so Django provides a
# shortcut for primary-key exact lookups.
# The following is identical to articles.get_object(id__exact=1).
>>> Article.objects.get_object(pk=1)
<Article object>

# Model instances of the same type and same ID are considered equal.
>>> a = Article.objects.get_object(pk=1)
>>> b = Article.objects.get_object(pk=1)
>>> a == b
True

# You can initialize a model instance using positional arguments, which should
# match the field order as defined in the model...
>>> a2 = Article(None, 'Second article', datetime(2005, 7, 29))
>>> a2.save()
>>> a2.id
2L
>>> a2.headline
'Second article'
>>> a2.pub_date
datetime.datetime(2005, 7, 29, 0, 0)

# ...or, you can use keyword arguments.
>>> a3 = Article(id=None, headline='Third article',
...    pub_date=datetime(2005, 7, 30))
>>> a3.save()
>>> a3.id
3L
>>> a3.headline
'Third article'
>>> a3.pub_date
datetime.datetime(2005, 7, 30, 0, 0)

# You can also mix and match position and keyword arguments, but be sure not to
# duplicate field information.
>>> a4 = Article(None, 'Fourth article', pub_date=datetime(2005, 7, 31))
>>> a4.save()
>>> a4.headline
'Fourth article'

# Don't use invalid keyword arguments.
>>> a5 = Article(id=None, headline='Invalid', pub_date=datetime(2005, 7, 31), foo='bar')
Traceback (most recent call last):
    ...
TypeError: 'foo' is an invalid keyword argument for this function

# You can leave off the ID.
>>> a5 = Article(headline='Article 6', pub_date=datetime(2005, 7, 31))
>>> a5.save()
>>> a5.id
5L
>>> a5.headline
'Article 6'

# If you leave off a field with "default" set, Django will use the default.
>>> a6 = Article(pub_date=datetime(2005, 7, 31))
>>> a6.save()
>>> a6.headline
'Default headline'

# For DateTimeFields, Django saves as much precision (in seconds) as you
# give it.
>>> a7 = Article(headline='Article 7', pub_date=datetime(2005, 7, 31, 12, 30))
>>> a7.save()
>>> Article.objects.get_object(id__exact=7).pub_date
datetime.datetime(2005, 7, 31, 12, 30)

>>> a8 = Article(headline='Article 8', pub_date=datetime(2005, 7, 31, 12, 30, 45))
>>> a8.save()
>>> Article.objects.get_object(id__exact=8).pub_date
datetime.datetime(2005, 7, 31, 12, 30, 45)
>>> a8.id
8L

# Saving an object again shouldn't create a new object -- it just saves the old one.
>>> a8.save()
>>> a8.id
8L
>>> a8.headline = 'Updated article 8'
>>> a8.save()
>>> a8.id
8L

>>> a7 == a8
False
>>> a8 == Article.objects.get_object(id__exact=8)
True
>>> a7 != a8
True
>>> Article.objects.get_object(id__exact=8) != Article.objects.get_object(id__exact=7)
True
>>> Article.objects.get_object(id__exact=8) == Article.objects.get_object(id__exact=7)
False

>>> Article.objects.get_pub_date_list('year')
[datetime.datetime(2005, 1, 1, 0, 0)]
>>> Article.objects.get_pub_date_list('month')
[datetime.datetime(2005, 7, 1, 0, 0)]
>>> Article.objects.get_pub_date_list('day')
[datetime.datetime(2005, 7, 28, 0, 0), datetime.datetime(2005, 7, 29, 0, 0), datetime.datetime(2005, 7, 30, 0, 0), datetime.datetime(2005, 7, 31, 0, 0)]
>>> Article.objects.get_pub_date_list('day', order='ASC')
[datetime.datetime(2005, 7, 28, 0, 0), datetime.datetime(2005, 7, 29, 0, 0), datetime.datetime(2005, 7, 30, 0, 0), datetime.datetime(2005, 7, 31, 0, 0)]
>>> Article.objects.get_pub_date_list('day', order='DESC')
[datetime.datetime(2005, 7, 31, 0, 0), datetime.datetime(2005, 7, 30, 0, 0), datetime.datetime(2005, 7, 29, 0, 0), datetime.datetime(2005, 7, 28, 0, 0)]

# An Article instance doesn't have access to the "objects" attribute.
# That is only available as a class method.
>>> a7.objects.get_list()
Traceback (most recent call last):
    ...
AttributeError: Manager isn't accessible via Article instances

>>> a7.objects
Traceback (most recent call last):
    ...
AttributeError: Manager isn't accessible via Article instances

"""

from django.conf import settings

building_docs = getattr(settings, 'BUILDING_DOCS', False)

if building_docs or settings.DATABASE_ENGINE == 'postgresql':
    API_TESTS += """
# In PostgreSQL, microsecond-level precision is available.
>>> a9 = Article(headline='Article 9', pub_date=datetime(2005, 7, 31, 12, 30, 45, 180))
>>> a9.save()
>>> Article.objects.get_object(id__exact=9).pub_date
datetime.datetime(2005, 7, 31, 12, 30, 45, 180)
"""

if building_docs or settings.DATABASE_ENGINE == 'mysql':
    API_TESTS += """
# In MySQL, microsecond-level precision isn't available. You'll lose
# microsecond-level precision once the data is saved.
>>> a9 = Article(headline='Article 9', pub_date=datetime(2005, 7, 31, 12, 30, 45, 180))
>>> a9.save()
>>> Article.objects.get_object(id__exact=9).pub_date
datetime.datetime(2005, 7, 31, 12, 30, 45)
"""

API_TESTS += """

# You can manually specify the primary key when creating a new objet
>>> a101 = Article(id=101, headline='Article 101', pub_date=datetime(2005, 7, 31, 12, 30, 45))
>>> a101.save()
>>> a101 = Article.objects.get_object(pk=101)
>>> a101.headline
'Article 101'
"""

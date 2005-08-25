"""
15. Subclassing models

You can subclass another model to create a copy of it that behaves slightly
differently.
"""

from django.core import meta

# From the "Bare-bones model" example
from django.models.basic import Article

# From the "Adding __repr__()" example
from django.models.repr import Article as ArticleWithRepr

# From the "Specifying ordering" example
from django.models.ordering import Article as ArticleWithOrdering

# This uses all fields and metadata from Article and
# adds a "section" field.
class ArticleWithSection(Article):
    section = meta.CharField(maxlength=30)
    class META:
       module_name = 'subarticles1'

# This uses all fields and metadata from Article but
# removes the "pub_date" field.
class ArticleWithoutPubDate(Article):
    class META:
       module_name = 'subarticles2'
       remove_fields = ('pub_date',)

# This uses all fields and metadata from Article but
# overrides the "pub_date" field.
class ArticleWithFieldOverride(Article):
    pub_date = meta.DateField() # overrides the old field, a DateTimeField
    class META:
        module_name = 'subarticles3'
        # No need to add remove_fields = ('pub_date',)

# This uses all fields and metadata from ArticleWithRepr and
# makes a few additions/changes.
class ArticleWithManyChanges(ArticleWithRepr):
    section = meta.CharField(maxlength=30)
    is_popular = meta.BooleanField()
    pub_date = meta.DateField() # overrides the old field, a DateTimeField
    class META:
       module_name = 'subarticles4'

# This uses all fields from ArticleWithOrdering but
# changes the ordering parameter.
class ArticleWithChangedMeta(ArticleWithOrdering):
    class META:
       module_name = 'subarticles5'
       ordering = ('headline', 'pub_date')

API_TESTS = """
# No data is in the system yet.
>>> subarticles1.get_list()
[]
>>> subarticles2.get_list()
[]
>>> subarticles3.get_list()
[]

# Create an ArticleWithSection.
>>> from datetime import date, datetime
>>> a1 = subarticles1.ArticleWithSection(headline='First', pub_date=datetime(2005, 8, 22), section='News')
>>> a1.save()
>>> a1
<ArticleWithSection object>
>>> a1.id
1
>>> a1.headline
'First'
>>> a1.pub_date
datetime.datetime(2005, 8, 22, 0, 0)

# Retrieve it again, to prove the fields have been saved.
>>> a1 = subarticles1.get_object(pk=1)
>>> a1.headline
'First'
>>> a1.pub_date
datetime.datetime(2005, 8, 22, 0, 0)
>>> a1.section
'News'

# Create an ArticleWithoutPubDate.
>>> a2 = subarticles2.ArticleWithoutPubDate(headline='Second')
>>> a2.save()
>>> a2
<ArticleWithoutPubDate object>
>>> a2.id
1
>>> a2.pub_date
Traceback (most recent call last):
    ...
AttributeError: 'ArticleWithoutPubDate' object has no attribute 'pub_date'

# Retrieve it again, to prove the fields have been saved.
>>> a2 = subarticles2.get_object(pk=1)
>>> a2.headline
'Second'
>>> a2.pub_date
Traceback (most recent call last):
    ...
AttributeError: 'ArticleWithoutPubDate' object has no attribute 'pub_date'

# Create an ArticleWithFieldOverride.
>>> a3 = subarticles3.ArticleWithFieldOverride(headline='Third', pub_date=date(2005, 8, 22))
>>> a3.save()
>>> a3
<ArticleWithFieldOverride object>
>>> a3.id
1
>>> a3.pub_date
datetime.date(2005, 8, 22)

# Retrieve it again, to prove the fields have been saved.
>>> a3 = subarticles3.get_object(pk=1)
>>> a3.headline
'Third'
>>> a3.pub_date
datetime.date(2005, 8, 22)

# Create an ArticleWithManyChanges.
>>> a4 = subarticles4.ArticleWithManyChanges(headline='Fourth', section='Arts',
...     is_popular=True, pub_date=date(2005, 8, 22))
>>> a4.save()

# a4 inherits __repr__() from its parent model (ArticleWithRepr).
>>> a4
Fourth

# Retrieve it again, to prove the fields have been saved.
>>> a4 = subarticles4.get_object(pk=1)
>>> a4.headline
'Fourth'
>>> a4.section
'Arts'
>>> a4.is_popular == True
True
>>> a4.pub_date
datetime.date(2005, 8, 22)

# Test get_list().
>>> subarticles1.get_list()
[<ArticleWithSection object>]
>>> subarticles2.get_list()
[<ArticleWithoutPubDate object>]
>>> subarticles3.get_list()
[<ArticleWithFieldOverride object>]
>>> subarticles4.get_list()
[Fourth]

# Create a couple of ArticleWithChangedMeta objects.
>>> a5 = subarticles5.ArticleWithChangedMeta(headline='A', pub_date=datetime(2005, 3, 1))
>>> a5.save()
>>> a6 = subarticles5.ArticleWithChangedMeta(headline='B', pub_date=datetime(2005, 4, 1))
>>> a6.save()
>>> a7 = subarticles5.ArticleWithChangedMeta(headline='C', pub_date=datetime(2005, 5, 1))
>>> a7.save()

# Ordering has been overridden, so objects are ordered
# by headline ASC instead of pub_date DESC.
>>> subarticles5.get_list()
[A, B, C]
"""

"""
15. Subclassing models

You can subclass another model to create a copy of it that behaves slightly
differently.
"""

from django.core import meta

# From the "Bare-bones model" example
from modeltests.basic.models import Article

# From the "Adding __repr__()" example
from modeltests.repr.models import Article as ArticleWithRepr

# From the "Specifying ordering" example
from modeltests.ordering.models import Article as ArticleWithOrdering

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

# These two models don't define a module_name.
class NoModuleNameFirst(Article):
    section = meta.CharField(maxlength=30)

class NoModuleNameSecond(Article):
    section = meta.CharField(maxlength=30)

API_TESTS = """
# No data is in the system yet.
>>> ArticleWithSection.objects.get_list()
[]
>>> ArticleWithoutPubDate.objects.get_list()
[]
>>> ArticleWithFieldOverride.objects.get_list()
[]

# Create an ArticleWithSection.
>>> from datetime import date, datetime
>>> a1 = ArticleWithSection(headline='First', pub_date=datetime(2005, 8, 22), section='News')
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
>>> a1 = ArticleWithSection.objects.get_object(pk=1)
>>> a1.headline
'First'
>>> a1.pub_date
datetime.datetime(2005, 8, 22, 0, 0)
>>> a1.section
'News'

# Create an ArticleWithoutPubDate.
>>> a2 = ArticleWithoutPubDate(headline='Second')
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
>>> a2 = ArticleWithoutPubDate.objects.get_object(pk=1)
>>> a2.headline
'Second'
>>> a2.pub_date
Traceback (most recent call last):
    ...
AttributeError: 'ArticleWithoutPubDate' object has no attribute 'pub_date'

# Create an ArticleWithFieldOverride.
>>> a3 = ArticleWithFieldOverride(headline='Third', pub_date=date(2005, 8, 22))
>>> a3.save()
>>> a3
<ArticleWithFieldOverride object>
>>> a3.id
1
>>> a3.pub_date
datetime.date(2005, 8, 22)

# Retrieve it again, to prove the fields have been saved.
>>> a3 = ArticleWithFieldOverride.objects.get_object(pk=1)
>>> a3.headline
'Third'
>>> a3.pub_date
datetime.date(2005, 8, 22)

# Create an ArticleWithManyChanges.
>>> a4 = ArticleWithManyChanges(headline='Fourth', section='Arts',
...     is_popular=True, pub_date=date(2005, 8, 22))
>>> a4.save()

# a4 inherits __repr__() from its parent model (ArticleWithRepr).
>>> a4
Fourth

# Retrieve it again, to prove the fields have been saved.
>>> a4 = ArticleWithManyChanges.objects.get_object(pk=1)
>>> a4.headline
'Fourth'
>>> a4.section
'Arts'
>>> a4.is_popular == True
True
>>> a4.pub_date
datetime.date(2005, 8, 22)

# Test get_list().
>>> ArticleWithSection.objects.get_list()
[<ArticleWithSection object>]
>>> ArticleWithoutPubDate.objects.get_list()
[<ArticleWithoutPubDate object>]
>>> ArticleWithFieldOverride.objects.get_list()
[<ArticleWithFieldOverride object>]
>>> ArticleWithManyChanges.objects.get_list()
[Fourth]

# Create a couple of ArticleWithChangedMeta objects.
>>> a5 = ArticleWithChangedMeta(headline='A', pub_date=datetime(2005, 3, 1))
>>> a5.save()
>>> a6 = ArticleWithChangedMeta(headline='B', pub_date=datetime(2005, 4, 1))
>>> a6.save()
>>> a7 = ArticleWithChangedMeta(headline='C', pub_date=datetime(2005, 5, 1))
>>> a7.save()

# Ordering has been overridden, so objects are ordered
# by headline ASC instead of pub_date DESC.
>>> ArticleWithChangedMeta.objects.get_list()
[A, B, C]

>>> NoModuleNameFirst.objects.get_list()
[]
>>> NoModuleNameSecond.objects.get_list()
[]
"""

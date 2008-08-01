"""
4. Many-to-one relationships

To define a many-to-one relationship, use ``ForeignKey()`` .
"""

from django.db import models

class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter)

    def __unicode__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)

__test__ = {'API_TESTS':"""
# Create a few Reporters.
>>> r = Reporter(first_name='John', last_name='Smith', email='john@example.com')
>>> r.save()

>>> r2 = Reporter(first_name='Paul', last_name='Jones', email='paul@example.com')
>>> r2.save()

# Create an Article.
>>> from datetime import datetime
>>> a = Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter=r)
>>> a.save()

>>> a.reporter.id
1

>>> a.reporter
<Reporter: John Smith>

# Article objects have access to their related Reporter objects.
>>> r = a.reporter

# These are strings instead of unicode strings because that's what was used in
# the creation of this reporter (and we haven't refreshed the data from the
# database, which always returns unicode strings).
>>> r.first_name, r.last_name
('John', 'Smith')

# Create an Article via the Reporter object.
>>> new_article = r.article_set.create(headline="John's second story", pub_date=datetime(2005, 7, 29))
>>> new_article
<Article: John's second story>
>>> new_article.reporter.id
1

# Create a new article, and add it to the article set.
>>> new_article2 = Article(headline="Paul's story", pub_date=datetime(2006, 1, 17))
>>> r.article_set.add(new_article2)
>>> new_article2.reporter.id
1
>>> r.article_set.all()
[<Article: John's second story>, <Article: Paul's story>, <Article: This is a test>]

# Add the same article to a different article set - check that it moves.
>>> r2.article_set.add(new_article2)
>>> new_article2.reporter.id
2
>>> r.article_set.all()
[<Article: John's second story>, <Article: This is a test>]
>>> r2.article_set.all()
[<Article: Paul's story>]

# Assign the article to the reporter directly using the descriptor
>>> new_article2.reporter = r
>>> new_article2.save()
>>> new_article2.reporter
<Reporter: John Smith>
>>> new_article2.reporter.id
1
>>> r.article_set.all()
[<Article: John's second story>, <Article: Paul's story>, <Article: This is a test>]
>>> r2.article_set.all()
[]

# Set the article back again using set descriptor.
>>> r2.article_set = [new_article, new_article2]
>>> r.article_set.all()
[<Article: This is a test>]
>>> r2.article_set.all()
[<Article: John's second story>, <Article: Paul's story>]

# Funny case - assignment notation can only go so far; because the
# ForeignKey cannot be null, existing members of the set must remain
>>> r.article_set = [new_article]
>>> r.article_set.all()
[<Article: John's second story>, <Article: This is a test>]
>>> r2.article_set.all()
[<Article: Paul's story>]

# Reporter cannot be null - there should not be a clear or remove method
>>> hasattr(r2.article_set, 'remove')
False
>>> hasattr(r2.article_set, 'clear')
False

# Reporter objects have access to their related Article objects.
>>> r.article_set.all()
[<Article: John's second story>, <Article: This is a test>]

>>> r.article_set.filter(headline__startswith='This')
[<Article: This is a test>]

>>> r.article_set.count()
2

>>> r2.article_set.count()
1

# Get articles by id
>>> Article.objects.filter(id__exact=1)
[<Article: This is a test>]
>>> Article.objects.filter(pk=1)
[<Article: This is a test>]

# Query on an article property
>>> Article.objects.filter(headline__startswith='This')
[<Article: This is a test>]

# The API automatically follows relationships as far as you need.
# Use double underscores to separate relationships.
# This works as many levels deep as you want. There's no limit.
# Find all Articles for any Reporter whose first name is "John".
>>> Article.objects.filter(reporter__first_name__exact='John')
[<Article: John's second story>, <Article: This is a test>]

# Check that implied __exact also works
>>> Article.objects.filter(reporter__first_name='John')
[<Article: John's second story>, <Article: This is a test>]

# Query twice over the related field.
>>> Article.objects.filter(reporter__first_name__exact='John', reporter__last_name__exact='Smith')
[<Article: John's second story>, <Article: This is a test>]

# The underlying query only makes one join when a related table is referenced twice.
>>> queryset = Article.objects.filter(reporter__first_name__exact='John', reporter__last_name__exact='Smith')
>>> sql = queryset.query.as_sql()[0]
>>> sql.count('INNER JOIN')
1

# The automatically joined table has a predictable name.
>>> Article.objects.filter(reporter__first_name__exact='John').extra(where=["many_to_one_reporter.last_name='Smith'"])
[<Article: John's second story>, <Article: This is a test>]

# And should work fine with the unicode that comes out of
# forms.Form.cleaned_data
>>> Article.objects.filter(reporter__first_name__exact='John').extra(where=["many_to_one_reporter.last_name='%s'" % u'Smith'])
[<Article: John's second story>, <Article: This is a test>]

# Find all Articles for the Reporter whose ID is 1.
# Use direct ID check, pk check, and object comparison
>>> Article.objects.filter(reporter__id__exact=1)
[<Article: John's second story>, <Article: This is a test>]
>>> Article.objects.filter(reporter__pk=1)
[<Article: John's second story>, <Article: This is a test>]
>>> Article.objects.filter(reporter=1)
[<Article: John's second story>, <Article: This is a test>]
>>> Article.objects.filter(reporter=r)
[<Article: John's second story>, <Article: This is a test>]

>>> Article.objects.filter(reporter__in=[1,2]).distinct()
[<Article: John's second story>, <Article: Paul's story>, <Article: This is a test>]
>>> Article.objects.filter(reporter__in=[r,r2]).distinct()
[<Article: John's second story>, <Article: Paul's story>, <Article: This is a test>]

# You can also use a queryset instead of a literal list of instances.
# The queryset must be reduced to a list of values using values(),
# then converted into a query
>>> Article.objects.filter(reporter__in=Reporter.objects.filter(first_name='John').values('pk').query).distinct()
[<Article: John's second story>, <Article: This is a test>]

# You need two underscores between "reporter" and "id" -- not one.
>>> Article.objects.filter(reporter_id__exact=1)
Traceback (most recent call last):
    ...
FieldError: Cannot resolve keyword 'reporter_id' into field. Choices are: headline, id, pub_date, reporter

# You need to specify a comparison clause
>>> Article.objects.filter(reporter_id=1)
Traceback (most recent call last):
    ...
FieldError: Cannot resolve keyword 'reporter_id' into field. Choices are: headline, id, pub_date, reporter

# You can also instantiate an Article by passing
# the Reporter's ID instead of a Reporter object.
>>> a3 = Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter_id=r.id)
>>> a3.save()
>>> a3.reporter.id
1
>>> a3.reporter
<Reporter: John Smith>

# Similarly, the reporter ID can be a string.
>>> a4 = Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter_id="1")
>>> a4.save()
>>> a4.reporter
<Reporter: John Smith>

# Reporters can be queried
>>> Reporter.objects.filter(id__exact=1)
[<Reporter: John Smith>]
>>> Reporter.objects.filter(pk=1)
[<Reporter: John Smith>]
>>> Reporter.objects.filter(first_name__startswith='John')
[<Reporter: John Smith>]

# Reporters can query in opposite direction of ForeignKey definition
>>> Reporter.objects.filter(article__id__exact=1)
[<Reporter: John Smith>]
>>> Reporter.objects.filter(article__pk=1)
[<Reporter: John Smith>]
>>> Reporter.objects.filter(article=1)
[<Reporter: John Smith>]
>>> Reporter.objects.filter(article=a)
[<Reporter: John Smith>]

>>> Reporter.objects.filter(article__in=[1,4]).distinct()
[<Reporter: John Smith>]
>>> Reporter.objects.filter(article__in=[1,a3]).distinct()
[<Reporter: John Smith>]
>>> Reporter.objects.filter(article__in=[a,a3]).distinct()
[<Reporter: John Smith>]

>>> Reporter.objects.filter(article__headline__startswith='This')
[<Reporter: John Smith>, <Reporter: John Smith>, <Reporter: John Smith>]
>>> Reporter.objects.filter(article__headline__startswith='This').distinct()
[<Reporter: John Smith>]

# Counting in the opposite direction works in conjunction with distinct()
>>> Reporter.objects.filter(article__headline__startswith='This').count()
3
>>> Reporter.objects.filter(article__headline__startswith='This').distinct().count()
1

# Queries can go round in circles.
>>> Reporter.objects.filter(article__reporter__first_name__startswith='John')
[<Reporter: John Smith>, <Reporter: John Smith>, <Reporter: John Smith>, <Reporter: John Smith>]
>>> Reporter.objects.filter(article__reporter__first_name__startswith='John').distinct()
[<Reporter: John Smith>]
>>> Reporter.objects.filter(article__reporter__exact=r).distinct()
[<Reporter: John Smith>]

# Check that implied __exact also works.
>>> Reporter.objects.filter(article__reporter=r).distinct()
[<Reporter: John Smith>]

# It's possible to use values() calls across many-to-one relations. (Note, too, that we clear the ordering here so as not to drag the 'headline' field into the columns being used to determine uniqueness.)
>>> d = {'reporter__first_name': u'John', 'reporter__last_name': u'Smith'}
>>> list(Article.objects.filter(reporter=r).distinct().order_by().values('reporter__first_name', 'reporter__last_name')) == [d]
True

# If you delete a reporter, his articles will be deleted.
>>> Article.objects.all()
[<Article: John's second story>, <Article: Paul's story>, <Article: This is a test>, <Article: This is a test>, <Article: This is a test>]
>>> Reporter.objects.order_by('first_name')
[<Reporter: John Smith>, <Reporter: Paul Jones>]
>>> r2.delete()
>>> Article.objects.all()
[<Article: John's second story>, <Article: This is a test>, <Article: This is a test>, <Article: This is a test>]
>>> Reporter.objects.order_by('first_name')
[<Reporter: John Smith>]

# You can delete using a JOIN in the query.
>>> Reporter.objects.filter(article__headline__startswith='This').delete()
>>> Reporter.objects.all()
[]
>>> Article.objects.all()
[]

# Check that Article.objects.select_related().dates() works properly when
# there are multiple Articles with the same date but different foreign-key
# objects (Reporters).
>>> r1 = Reporter.objects.create(first_name='Mike', last_name='Royko', email='royko@suntimes.com')
>>> r2 = Reporter.objects.create(first_name='John', last_name='Kass', email='jkass@tribune.com')
>>> a1 = Article.objects.create(headline='First', pub_date=datetime(1980, 4, 23), reporter=r1)
>>> a2 = Article.objects.create(headline='Second', pub_date=datetime(1980, 4, 23), reporter=r2)
>>> Article.objects.select_related().dates('pub_date', 'day')
[datetime.datetime(1980, 4, 23, 0, 0)]
>>> Article.objects.select_related().dates('pub_date', 'month')
[datetime.datetime(1980, 4, 1, 0, 0)]
>>> Article.objects.select_related().dates('pub_date', 'year')
[datetime.datetime(1980, 1, 1, 0, 0)]
"""}

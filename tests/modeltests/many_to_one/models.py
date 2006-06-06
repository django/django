"""
4. Many-to-one relationships

To define a many-to-one relationship, use ``ForeignKey()`` .
"""

from django.db import models

class Reporter(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    email = models.EmailField()

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter)

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)

API_TESTS = """
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

# Query twice over the related field.
>>> Article.objects.filter(reporter__first_name__exact='John', reporter__last_name__exact='Smith')
[<Article: John's second story>, <Article: This is a test>]

# The underlying query only makes one join when a related table is referenced twice.
>>> query = Article.objects.filter(reporter__first_name__exact='John', reporter__last_name__exact='Smith')
>>> null, sql, null = query._get_sql_clause()
>>> sql.count('INNER JOIN')
1

# The automatically joined table has a predictable name.
>>> Article.objects.filter(reporter__first_name__exact='John').extra(where=["many_to_one_article__reporter.last_name='Smith'"])
[<Article: John's second story>, <Article: This is a test>]

# Find all Articles for the Reporter whose ID is 1.
>>> Article.objects.filter(reporter__id__exact=1)
[<Article: John's second story>, <Article: This is a test>]
>>> Article.objects.filter(reporter__pk=1)
[<Article: John's second story>, <Article: This is a test>]

# You need two underscores between "reporter" and "id" -- not one.
>>> Article.objects.filter(reporter_id__exact=1)
Traceback (most recent call last):
    ...
TypeError: Cannot resolve keyword 'reporter_id' into field

# You need to specify a comparison clause
>>> Article.objects.filter(reporter_id=1)
Traceback (most recent call last):
    ...
TypeError: Cannot resolve keyword 'reporter_id' into field

# "pk" shortcut syntax works in a related context, too.
>>> Article.objects.filter(reporter__pk=1)
[<Article: John's second story>, <Article: This is a test>]

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

# Deletes using a join in the query
>>> Reporter.objects.filter(article__headline__startswith='This').delete()
>>> Reporter.objects.all()
[]
>>> Article.objects.all()
[]

"""

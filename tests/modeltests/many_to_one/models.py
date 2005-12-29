"""
4. Many-to-one relationships

To define a many-to-one relationship, use ``ForeignKey()`` .
"""

from django.db import models

class Reporter(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    email = models.EmailField()

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter)

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a Reporter.
>>> r = Reporter(first_name='John', last_name='Smith', email='john@example.com')
>>> r.save()

# Create an Article.
>>> from datetime import datetime
>>> a = Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter=r)
>>> a.save()

>>> a.reporter_id
1

>>> a.get_reporter()
John Smith

# Article objects have access to their related Reporter objects.
>>> r = a.get_reporter()
>>> r.first_name, r.last_name
('John', 'Smith')

# Create an Article via the Reporter object.
>>> new_article = r.add_article(headline="John's second story", pub_date=datetime(2005, 7, 29))
>>> new_article
John's second story
>>> new_article.reporter_id
1

# Reporter objects have access to their related Article objects.
>>> r.get_article_list(order_by=['pub_date'])
[This is a test, John's second story]

>>> r.get_article(headline__startswith='This')
This is a test

>>> r.get_article_count()
2

# The API automatically follows relationships as far as you need.
# Use double underscores to separate relationships.
# This works as many levels deep as you want. There's no limit.
# Find all Articles for any Reporter whose first name is "John".
>>> Article.objects.get_list(reporter__first_name__exact='John', order_by=['pub_date'])
[This is a test, John's second story]

# Query twice over the related field.
>>> Article.objects.get_list(reporter__first_name__exact='John', reporter__last_name__exact='Smith')
[This is a test, John's second story]

# The underlying query only makes one join when a related table is referenced twice.
>>> null, sql, null = Article.objects._get_sql_clause(reporter__first_name__exact='John', reporter__last_name__exact='Smith')
>>> sql.count('INNER JOIN')
1

# The automatically joined table has a predictable name.
>>> Article.objects.get_list(reporter__first_name__exact='John', where=["many_to_one_articles__reporter.last_name='Smith'"])
[This is a test, John's second story]

# Find all Articles for the Reporter whose ID is 1.
>>> Article.objects.get_list(reporter__id__exact=1, order_by=['pub_date'])
[This is a test, John's second story]

# Note you need two underscores between "reporter" and "id" -- not one.
>>> Article.objects.get_list(reporter_id__exact=1)
Traceback (most recent call last):
    ...
TypeError: got unexpected keyword argument 'reporter_id__exact'

# "pk" shortcut syntax works in a related context, too.
>>> Article.objects.get_list(reporter__pk=1, order_by=['pub_date'])
[This is a test, John's second story]

# You can also instantiate an Article by passing
# the Reporter's ID instead of a Reporter object.
>>> a3 = Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter_id=r.id)
>>> a3.save()
>>> a3.reporter_id
1
>>> a3.get_reporter()
John Smith

# Similarly, the reporter ID can be a string.
>>> a4 = Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter_id="1")
>>> a4.save()
>>> a4.get_reporter()
John Smith

"""

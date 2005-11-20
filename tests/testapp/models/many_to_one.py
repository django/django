"""
4. Many-to-one relationships

To define a many-to-one relationship, use ``ForeignKey()`` .
"""

from django.core import meta

class Reporter(meta.Model):
    first_name = meta.CharField(maxlength=30)
    last_name = meta.CharField(maxlength=30)
    email = meta.EmailField()

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Article(meta.Model):
    headline = meta.CharField(maxlength=100)
    pub_date = meta.DateField()
    reporter = meta.ForeignKey(Reporter)

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a Reporter.
>>> r = reporters.Reporter(first_name='John', last_name='Smith', email='john@example.com')
>>> r.save()

# Create an Article.
>>> from datetime import datetime
>>> a = articles.Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter=r)
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
>>> articles.get_list(reporter__first_name__exact='John', order_by=['pub_date'])
[This is a test, John's second story]

# Find all Articles for the Reporter whose ID is 1.
>>> articles.get_list(reporter__id__exact=1, order_by=['pub_date'])
[This is a test, John's second story]

# Note you need two underscores between "reporter" and "id" -- not one.
>>> articles.get_list(reporter_id__exact=1)
Traceback (most recent call last):
    ...
TypeError: got unexpected keyword argument 'reporter_id__exact'

# "pk" shortcut syntax works in a related context, too.
>>> articles.get_list(reporter__pk=1, order_by=['pub_date'])
[This is a test, John's second story]

# You can also instantiate an Article by passing
# the Reporter's ID instead of a Reporter object.
>>> a3 = articles.Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter_id=r.id)
>>> a3.save()
>>> a3.reporter_id
1
>>> a3.get_reporter()
John Smith

# Similarly, the reporter ID can be a string.
>>> a4 = articles.Article(id=None, headline="This is a test", pub_date=datetime(2005, 7, 27), reporter_id="1")
>>> a4.save()
>>> a4.get_reporter()
John Smith
"""

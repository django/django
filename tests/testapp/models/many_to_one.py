"""
4. Many-to-one relationships

To define a many-to-one relationship, use ForeignKey().
"""

from django.core import meta

class Reporter(meta.Model):
    fields = (
        meta.CharField('first_name', maxlength=30),
        meta.CharField('last_name', maxlength=30),
    )

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Article(meta.Model):
    fields = (
        meta.CharField('headline', maxlength=100),
        meta.DateField('pub_date'),
        meta.ForeignKey(Reporter),
    )

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a Reporter.
>>> r = reporters.Reporter(id=None, first_name='John', last_name='Smith')
>>> r.save()

# Create an Article.
>>> from datetime import datetime
>>> a = articles.Article(id=None, headline='This is a test', pub_date=datetime(2005, 7, 27), reporter_id=r.id)
>>> a.save()

>>> a.reporter_id
1L

>>> a.get_reporter()
John Smith

# Article objects have access to their related Reporter objects.
>>> r = a.get_reporter()
>>> r.first_name, r.last_name
('John', 'Smith')

# Create an Article via the Reporter object.
>>> new_article = r.add_article(headline="John's second story", pub_date=datetime(2005, 7, 28))
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
2L

# The API automatically follows relationships as far as you need.
# Use double underscores to separate relationships.
# This works as many levels deep as you want. There's no limit.
# Find all Articles for any Reporter whose first name is "John".
>>> articles.get_list(reporter__first_name__exact='John', order_by=['pub_date'])
[This is a test, John's second story]

"""

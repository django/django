"""
9. Many-to-many relationships via an intermediary table

For many-to-many relationships that need extra fields on the intermediary
table, use an intermediary model.

In this example, an ``Article`` can have multiple ``Reporter``s, and each
``Article``-``Reporter`` combination (a ``Writer``) has a ``position`` field,
which specifies the ``Reporter``'s position for the given article (e.g. "Staff
writer").
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
    )

    def __repr__(self):
        return self.headline

class Writer(meta.Model):
    fields = (
        meta.ForeignKey(Reporter),
        meta.ForeignKey(Article),
        meta.CharField('position', maxlength=100),
    )

    def __repr__(self):
        return '%r (%s)' % (self.get_reporter(), self.position)

API_TESTS = """
# Create a few Reporters.
>>> r1 = reporters.Reporter(id=None, first_name='John', last_name='Smith')
>>> r1.save()
>>> r2 = reporters.Reporter(id=None, first_name='Jane', last_name='Doe')
>>> r2.save()

# Create an Article.
>>> from datetime import datetime
>>> a = articles.Article(id=None, headline='This is a test', pub_date=datetime(2005, 7, 27))
>>> a.save()

# Create a few Writers.
>>> w1 = writers.Writer(id=None, reporter_id=r1.id, article_id=a.id, position='Main writer')
>>> w1.save()
>>> w2 = writers.Writer(id=None, reporter_id=r2.id, article_id=a.id, position='Contributor')
>>> w2.save()

# Play around with the API.
>>> a.get_writer_list(order_by=['-position'], select_related=True)
[John Smith (Main writer), Jane Doe (Contributor)]
>>> w1.get_reporter()
John Smith
>>> w2.get_reporter()
Jane Doe
>>> w1.get_article()
This is a test
>>> w2.get_article()
This is a test
>>> r1.get_writer_list()
[John Smith (Main writer)]
"""

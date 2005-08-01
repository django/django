"""
7. The lookup API

This demonstrates features of the database API.
"""

from django.core import meta

class Article(meta.Model):
    fields = (
        meta.CharField('headline', maxlength=100),
        meta.DateTimeField('pub_date'),
    )
    ordering = ('-pub_date', 'headline')

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a couple of Articles.
>>> from datetime import datetime
>>> a1 = articles.Article(id=None, headline='Article 1', pub_date=datetime(2005, 7, 26))
>>> a1.save()
>>> a2 = articles.Article(id=None, headline='Article 2', pub_date=datetime(2005, 7, 27))
>>> a2.save()
>>> a3 = articles.Article(id=None, headline='Article 3', pub_date=datetime(2005, 7, 27))
>>> a3.save()
>>> a4 = articles.Article(id=None, headline='Article 4', pub_date=datetime(2005, 7, 28))
>>> a4.save()

# get_iterator() is just like get_list(), but it's a generator.
>>> for a in articles.get_iterator():
...     print a.headline
Article 4
Article 2
Article 3
Article 1

# get_iterator() takes the same lookup arguments as get_list().
>>> for a in articles.get_iterator(headline__endswith='4'):
...     print a.headline
Article 4

# get_count() returns the number of objects matching search criteria.
>>> articles.get_count()
4L
>>> articles.get_count(pub_date__exact=datetime(2005, 7, 27))
2L
>>> articles.get_count(headline__startswith='Blah blah')
0L

# get_in_bulk() takes a list of IDs and returns a dictionary mapping IDs
# to objects.
>>> articles.get_in_bulk([1, 2])
{1: Article 1, 2: Article 2}
>>> articles.get_in_bulk([3])
{3: Article 3}
>>> articles.get_in_bulk([1000])
{}

# get_values() is just like get_list(), except it returns a list of
# dictionaries instead of object instances -- and you can specify which fields
# you want to retrieve.
>>> articles.get_values(fields=['headline'])
[{'headline': 'Article 4'}, {'headline': 'Article 2'}, {'headline': 'Article 3'}, {'headline': 'Article 1'}]
>>> articles.get_values(pub_date__exact=datetime(2005, 7, 27), fields=['id'])
[{'id': 2}, {'id': 3}]
>>> articles.get_values(fields=['id', 'headline']) == [{'id': 4, 'headline': 'Article 4'}, {'id': 2, 'headline': 'Article 2'}, {'id': 3, 'headline': 'Article 3'}, {'id': 1, 'headline': 'Article 1'}]
True

# get_values_iterator() is just like get_values(), but it's a generator.
>>> for d in articles.get_values_iterator(fields=['id', 'headline']):
...     i = d.items()
...     i.sort()
...     i
[('headline', 'Article 4'), ('id', 4)]
[('headline', 'Article 2'), ('id', 2)]
[('headline', 'Article 3'), ('id', 3)]
[('headline', 'Article 1'), ('id', 1)]

# Every DateField and DateTimeField creates get_next_by_FOO() and
# get_previous_by_FOO() methods.
>>> a3.get_next_by_pub_date()
Article 4
>>> a2.get_previous_by_pub_date()
Article 1

"""

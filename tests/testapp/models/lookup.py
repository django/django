"""
7. The lookup API

This demonstrates features of the database API.
"""

from django.core import meta

class Article(meta.Model):
    headline = meta.CharField(maxlength=100)
    pub_date = meta.DateTimeField()
    class META:
        ordering = ('-pub_date', 'headline')

    def __repr__(self):
        return self.headline

API_TESTS = """
# Create a couple of Articles.
>>> from datetime import datetime
>>> a1 = articles.Article(headline='Article 1', pub_date=datetime(2005, 7, 26))
>>> a1.save()
>>> a2 = articles.Article(headline='Article 2', pub_date=datetime(2005, 7, 27))
>>> a2.save()
>>> a3 = articles.Article(headline='Article 3', pub_date=datetime(2005, 7, 27))
>>> a3.save()
>>> a4 = articles.Article(headline='Article 4', pub_date=datetime(2005, 7, 28))
>>> a4.save()
>>> a5 = articles.Article(headline='Article 5', pub_date=datetime(2005, 8, 1, 9, 0))
>>> a5.save()
>>> a6 = articles.Article(headline='Article 6', pub_date=datetime(2005, 8, 1, 8, 0))
>>> a6.save()
>>> a7 = articles.Article(headline='Article 7', pub_date=datetime(2005, 7, 27))
>>> a7.save()

# get_iterator() is just like get_list(), but it's a generator.
>>> for a in articles.get_iterator():
...     print a.headline
Article 5
Article 6
Article 4
Article 2
Article 3
Article 7
Article 1

# get_iterator() takes the same lookup arguments as get_list().
>>> for a in articles.get_iterator(headline__endswith='4'):
...     print a.headline
Article 4

# get_count() returns the number of objects matching search criteria.
>>> articles.get_count()
7L
>>> articles.get_count(pub_date__exact=datetime(2005, 7, 27))
3L
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
[{'headline': 'Article 5'}, {'headline': 'Article 6'}, {'headline': 'Article 4'}, {'headline': 'Article 2'}, {'headline': 'Article 3'}, {'headline': 'Article 7'}, {'headline': 'Article 1'}]
>>> articles.get_values(pub_date__exact=datetime(2005, 7, 27), fields=['id'])
[{'id': 2}, {'id': 3}, {'id': 7}]
>>> articles.get_values(fields=['id', 'headline']) == [{'id': 5, 'headline': 'Article 5'}, {'id': 6, 'headline': 'Article 6'}, {'id': 4, 'headline': 'Article 4'}, {'id': 2, 'headline': 'Article 2'}, {'id': 3, 'headline': 'Article 3'}, {'id': 7, 'headline': 'Article 7'}, {'id': 1, 'headline': 'Article 1'}]
True

# get_values_iterator() is just like get_values(), but it's a generator.
>>> for d in articles.get_values_iterator(fields=['id', 'headline']):
...     i = d.items()
...     i.sort()
...     i
[('headline', 'Article 5'), ('id', 5)]
[('headline', 'Article 6'), ('id', 6)]
[('headline', 'Article 4'), ('id', 4)]
[('headline', 'Article 2'), ('id', 2)]
[('headline', 'Article 3'), ('id', 3)]
[('headline', 'Article 7'), ('id', 7)]
[('headline', 'Article 1'), ('id', 1)]

# Every DateField and DateTimeField creates get_next_by_FOO() and
# get_previous_by_FOO() methods.
# In the case of identical date values, these methods will use the ID as a
# fallback check. This guarantees that no records are skipped or duplicated.
>>> a1.get_next_by_pub_date()
Article 2
>>> a2.get_next_by_pub_date()
Article 3
>>> a3.get_next_by_pub_date()
Article 7
>>> a4.get_next_by_pub_date()
Article 6
>>> a5.get_next_by_pub_date()
Traceback (most recent call last):
    ...
ArticleDoesNotExist: Article does not exist for ...
>>> a6.get_next_by_pub_date()
Article 5
>>> a7.get_next_by_pub_date()
Article 4

>>> a7.get_previous_by_pub_date()
Article 3
>>> a6.get_previous_by_pub_date()
Article 4
>>> a5.get_previous_by_pub_date()
Article 6
>>> a4.get_previous_by_pub_date()
Article 7
>>> a3.get_previous_by_pub_date()
Article 2
>>> a2.get_previous_by_pub_date()
Article 1

# Underscores and percent signs have special meaning in the underlying
# database library, but Django handles the quoting of them automatically.
>>> a8 = articles.Article(headline='Article_ with underscore', pub_date=datetime(2005, 11, 20))
>>> a8.save()
>>> articles.get_list(headline__startswith='Article')
[Article_ with underscore, Article 5, Article 6, Article 4, Article 2, Article 3, Article 7, Article 1]
>>> articles.get_list(headline__startswith='Article_')
[Article_ with underscore]
>>> a9 = articles.Article(headline='Article% with percent sign', pub_date=datetime(2005, 11, 21))
>>> a9.save()
>>> articles.get_list(headline__startswith='Article')
[Article% with percent sign, Article_ with underscore, Article 5, Article 6, Article 4, Article 2, Article 3, Article 7, Article 1]
>>> articles.get_list(headline__startswith='Article%')
[Article% with percent sign]
"""

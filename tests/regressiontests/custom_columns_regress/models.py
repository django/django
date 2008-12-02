"""
Regression for #9736.

Checks some pathological column naming to make sure it doesn't break
table creation or queries.

"""

from django.db import models

class Article(models.Model):
    Article_ID = models.AutoField(primary_key=True, db_column='Article ID')
    headline = models.CharField(max_length=100)
    authors = models.ManyToManyField('Author', db_table='my m2m table')
    primary_author = models.ForeignKey('Author', db_column='Author ID', related_name='primary_set')

    def __unicode__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)

class Author(models.Model):
    Author_ID = models.AutoField(primary_key=True, db_column='Author ID')
    first_name = models.CharField(max_length=30, db_column='first name')
    last_name = models.CharField(max_length=30, db_column='last name')

    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)

    class Meta:
        db_table = 'my author table'
        ordering = ('last_name','first_name')


__test__ = {'API_TESTS':"""
# Create a Author.
>>> a = Author(first_name='John', last_name='Smith')
>>> a.save()

>>> a.Author_ID
1

# Create another author
>>> a2 = Author(first_name='Peter', last_name='Jones')
>>> a2.save()

# Create an article
>>> art = Article(headline='Django lets you build web apps easily', primary_author=a)
>>> art.save()
>>> art.authors = [a, a2]

# Although the table and column names on Author have been set to custom values,
# nothing about using the Author model has changed...

# Query the available authors
>>> Author.objects.all()
[<Author: Peter Jones>, <Author: John Smith>]

>>> Author.objects.filter(first_name__exact='John')
[<Author: John Smith>]

>>> Author.objects.get(first_name__exact='John')
<Author: John Smith>

>>> Author.objects.filter(firstname__exact='John')
Traceback (most recent call last):
    ...
FieldError: Cannot resolve keyword 'firstname' into field. Choices are: Author_ID, article, first_name, last_name, primary_set

>>> a = Author.objects.get(last_name__exact='Smith')
>>> a.first_name
u'John'
>>> a.last_name
u'Smith'
>>> a.firstname
Traceback (most recent call last):
    ...
AttributeError: 'Author' object has no attribute 'firstname'
>>> a.last
Traceback (most recent call last):
    ...
AttributeError: 'Author' object has no attribute 'last'

# Although the Article table uses a custom m2m table,
# nothing about using the m2m relationship has changed...

# Get all the authors for an article
>>> art.authors.all()
[<Author: Peter Jones>, <Author: John Smith>]

# Get the articles for an author
>>> a.article_set.all()
[<Article: Django lets you build web apps easily>]

# Query the authors across the m2m relation
>>> art.authors.filter(last_name='Jones')
[<Author: Peter Jones>]

"""}

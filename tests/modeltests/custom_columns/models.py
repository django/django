"""
17. Custom column/table names

If your database column name is different than your model attribute, use the
``db_column`` parameter. Note that you'll use the field's name, not its column
name, in API usage.

If your database table name is different than your model name, use the
``db_table`` Meta attribute. This has no effect on the API used to 
query the database.

If you need to use a table name for a many-to-many relationship that differs 
from the default generated name, use the ``db_table`` parameter on the 
ManyToMany field. This has no effect on the API for querying the database.

"""

from django.db import models

class Author(models.Model):
    first_name = models.CharField(maxlength=30, db_column='firstname')
    last_name = models.CharField(maxlength=30, db_column='last')

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

    class Meta:
        db_table = 'my_author_table'
        ordering = ('last_name','first_name')

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    authors = models.ManyToManyField(Author, db_table='my_m2m_table')

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)
        
__test__ = {'API_TESTS':"""
# Create a Author.
>>> a = Author(first_name='John', last_name='Smith')
>>> a.save()

>>> a.id
1

# Create another author
>>> a2 = Author(first_name='Peter', last_name='Jones')
>>> a2.save()

# Create an article
>>> art = Article(headline='Django lets you build web apps easily')
>>> art.save()
>>> art.authors = [a, a2]

# Although the table and column names on Author have been set to 
# custom values, nothing about using the Author model has changed...

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
TypeError: Cannot resolve keyword 'firstname' into field

>>> a = Author.objects.get(last_name__exact='Smith')
>>> a.first_name
'John'
>>> a.last_name
'Smith'
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

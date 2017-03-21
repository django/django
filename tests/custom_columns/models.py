"""
Custom column/table names

If your database column name is different than your model attribute, use the
``db_column`` parameter. Note that you'll use the field's name, not its column
name, in API usage.

If your database table name is different than your model name, use the
``db_table`` Meta attribute. This has no effect on the API used to
query the database.

If you need to use a table name for a many-to-many relationship that differs
from the default generated name, use the ``db_table`` parameter on the
``ManyToManyField``. This has no effect on the API for querying the database.

"""

from django.db import models


class Author(models.Model):
    Author_ID = models.AutoField(primary_key=True, db_column='Author ID')
    first_name = models.CharField(max_length=30, db_column='firstname')
    last_name = models.CharField(max_length=30, db_column='last')

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

    class Meta:
        db_table = 'my_author_table'
        ordering = ('last_name', 'first_name')


class Article(models.Model):
    Article_ID = models.AutoField(primary_key=True, db_column='Article ID')
    headline = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author, db_table='my_m2m_table')
    primary_author = models.ForeignKey(
        Author,
        models.SET_NULL,
        db_column='Author ID',
        related_name='primary_set',
        null=True,
    )

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)

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




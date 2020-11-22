"""
Callable defaults

You can pass callable objects as the ``default`` parameter to a field. When
the object is created without an explicit value passed in, Django will call
the method to determine the default value.

This example uses ``datetime.datetime.now`` as the default for the ``pub_date``
field.
"""

from datetime import datetime

from django.db import models
from django.db.models.functions import Coalesce, ExtractYear, Now, Pi


class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.headline


class DBArticle(models.Model):
    """
    An article using database defaults.

    You can pass values or expressions as the ``db_default`` parameter
    to a field. When the object is created without an explicit value
    passed in, the database will insert the default value automatically.

    This example uses ``django.db.models.functions.Now`` as the default
    for the ``pub_date`` field.
    """

    headline = models.CharField(max_length=100, db_default='Default headline')
    pub_date = models.DateTimeField(db_default=Now())

    def __str__(self):
        return self.headline


class DBDefaults(models.Model):
    both = models.IntegerField(default=1, db_default=2)
    null = models.FloatField(null=True, db_default=1.1)


class DBDefaultsFunction(models.Model):
    number = models.FloatField(db_default=Pi())
    year = models.IntegerField(db_default=ExtractYear(Now()))
    added = models.FloatField(db_default=Pi() + 4.5)
    multiple_subfunctions = models.FloatField(db_default=Coalesce(4.5, Pi()))

    class Meta:
        required_db_features = {'supports_functions_in_defaults'}


class DBDefaultsPK(models.Model):
    language_code = models.CharField(primary_key=True, max_length=2, db_default='en')

    class Meta:
        required_db_vendor = 'postgresql'


class DBDefaultsFK(models.Model):
    language_code = models.ForeignKey(
        DBDefaultsPK, db_default='fr', on_delete=models.CASCADE
    )

    class Meta:
        required_db_vendor = 'postgresql'

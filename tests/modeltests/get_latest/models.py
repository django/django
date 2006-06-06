"""
8. get_latest_by

Models can have a ``get_latest_by`` attribute, which should be set to the name
of a DateField or DateTimeField. If ``get_latest_by`` exists, the model's
module will get a ``get_latest()`` function, which will return the latest
object in the database according to that field. "Latest" means "having the
date farthest into the future."
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateField()
    expire_date = models.DateField()
    class Meta:
        get_latest_by = 'pub_date'

    def __str__(self):
        return self.headline

class Person(models.Model):
    name = models.CharField(maxlength=30)
    birthday = models.DateField()

    # Note that this model doesn't have "get_latest_by" set.

    def __str__(self):
        return self.name

API_TESTS = """
# Because no Articles exist yet, get_latest() raises ArticleDoesNotExist.
>>> Article.objects.latest()
Traceback (most recent call last):
    ...
DoesNotExist: Article matching query does not exist.

# Create a couple of Articles.
>>> from datetime import datetime
>>> a1 = Article(headline='Article 1', pub_date=datetime(2005, 7, 26), expire_date=datetime(2005, 9, 1))
>>> a1.save()
>>> a2 = Article(headline='Article 2', pub_date=datetime(2005, 7, 27), expire_date=datetime(2005, 7, 28))
>>> a2.save()
>>> a3 = Article(headline='Article 3', pub_date=datetime(2005, 7, 27), expire_date=datetime(2005, 8, 27))
>>> a3.save()
>>> a4 = Article(headline='Article 4', pub_date=datetime(2005, 7, 28), expire_date=datetime(2005, 7, 30))
>>> a4.save()

# Get the latest Article.
>>> Article.objects.latest()
<Article: Article 4>

# Get the latest Article that matches certain filters.
>>> Article.objects.filter(pub_date__lt=datetime(2005, 7, 27)).latest()
<Article: Article 1>

# Pass a custom field name to latest() to change the field that's used to
# determine the latest object.
>>> Article.objects.latest('expire_date')
<Article: Article 1>

>>> Article.objects.filter(pub_date__gt=datetime(2005, 7, 26)).latest('expire_date')
<Article: Article 3>

# You can still use latest() with a model that doesn't have "get_latest_by"
# set -- just pass in the field name manually.
>>> p1 = Person(name='Ralph', birthday=datetime(1950, 1, 1))
>>> p1.save()
>>> p2 = Person(name='Stephanie', birthday=datetime(1960, 2, 3))
>>> p2.save()
>>> Person.objects.latest()
Traceback (most recent call last):
    ...
AssertionError: latest() requires either a field_name parameter or 'get_latest_by' in the model

>>> Person.objects.latest('birthday')
<Person: Stephanie>
"""

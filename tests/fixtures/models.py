"""
Fixtures.

Fixtures are a way of loading data into the database in bulk. Fixure data
can be stored in any serializable format (including JSON and XML). Fixtures
are identified by name, and are stored in either a directory named 'fixtures'
in the application directory, or in one of the directories named in the
``FIXTURE_DIRS`` setting.
"""

import uuid

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Category(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)


class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('-pub_date', 'headline')


class Blog(models.Model):
    name = models.CharField(max_length=100)
    featured = models.ForeignKey(Article, models.CASCADE, related_name='fixtures_featured_set')
    articles = models.ManyToManyField(Article, blank=True,
                                      related_name='fixtures_articles_set')

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100)
    tagged_type = models.ForeignKey(ContentType, models.CASCADE, related_name="fixtures_tag_set")
    tagged_id = models.PositiveIntegerField(default=0)
    tagged = GenericForeignKey(ct_field='tagged_type', fk_field='tagged_id')

    def __str__(self):
        return '<%s: %s> tagged "%s"' % (self.tagged.__class__.__name__,
                                         self.tagged, self.name)


class PersonManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Person(models.Model):
    objects = PersonManager()
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)

    def natural_key(self):
        return (self.name,)


class SpyManager(PersonManager):
    def get_queryset(self):
        return super().get_queryset().filter(cover_blown=False)


class Spy(Person):
    objects = SpyManager()
    cover_blown = models.BooleanField(default=False)


class ProxySpy(Spy):
    class Meta:
        proxy = True


class Visa(models.Model):
    person = models.ForeignKey(Person, models.CASCADE)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return '%s %s' % (self.person.name,
                          ', '.join(p.name for p in self.permissions.all()))


class Book(models.Model):
    name = models.CharField(max_length=100)
    authors = models.ManyToManyField(Person)

    def __str__(self):
        authors = ' and '.join(a.name for a in self.authors.all())
        return '%s by %s' % (self.name, authors) if authors else self.name

    class Meta:
        ordering = ('name',)


class PrimaryKeyUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

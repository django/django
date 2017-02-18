from __future__ import unicode_literals

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Square(models.Model):
    root = models.IntegerField()
    square = models.PositiveIntegerField()

    def __str__(self):
        return "%s ** 2 == %s" % (self.root, self.square)


@python_2_unicode_compatible
class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)


class SchoolClass(models.Model):
    year = models.PositiveIntegerField()
    day = models.CharField(max_length=9, blank=True)
    last_updated = models.DateTimeField()


class VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ(models.Model):
    class Meta:
        # We need to use a short actual table name or
        # we hit issue #8548 which we're not testing!
        verbose_name = 'model_with_long_table_name'
    primary_key_is_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz = models.AutoField(primary_key=True)
    charfield_is_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz = models.CharField(max_length=100)
    m2m_also_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz = models.ManyToManyField(Person, blank=True)


class Tag(models.Model):
    name = models.CharField(max_length=30)
    content_type = models.ForeignKey(ContentType, related_name='backend_tags')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class Post(models.Model):
    name = models.CharField(max_length=30)
    text = models.TextField()
    tags = GenericRelation('Tag')

    class Meta:
        db_table = 'CaseSensitive_Post'


@python_2_unicode_compatible
class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class ReporterProxy(Reporter):
    class Meta:
        proxy = True


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter)
    reporter_proxy = models.ForeignKey(ReporterProxy, null=True,
                                       related_name='reporter_proxy')

    def __str__(self):
        return self.headline


@python_2_unicode_compatible
class Item(models.Model):
    name = models.CharField(max_length=30)
    date = models.DateField()
    time = models.TimeField()
    last_modified = models.DateTimeField()

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Object(models.Model):
    related_objects = models.ManyToManyField("self", db_constraint=False, symmetrical=False)

    def __str__(self):
        return str(self.id)


@python_2_unicode_compatible
class ObjectReference(models.Model):
    obj = models.ForeignKey(Object, db_constraint=False)

    def __str__(self):
        return str(self.obj_id)


class RawData(models.Model):
    raw_data = models.BinaryField()

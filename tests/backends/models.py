from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Square(models.Model):
    root = models.IntegerField()
    square = models.PositiveIntegerField()

    def __str__(self):
        return "%s ** 2 == %s" % (self.root, self.square)


class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)


class SchoolClassManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(year=1000)


class SchoolClass(models.Model):
    year = models.PositiveIntegerField()
    day = models.CharField(max_length=9, blank=True)
    last_updated = models.DateTimeField()

    objects = SchoolClassManager()


class VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ(models.Model):
    primary_key_is_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz = models.AutoField(primary_key=True)
    charfield_is_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz = models.CharField(max_length=100)
    m2m_also_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz = models.ManyToManyField(Person, blank=True)


class Tag(models.Model):
    name = models.CharField(max_length=30)
    content_type = models.ForeignKey(ContentType, models.CASCADE, related_name='backend_tags')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class Post(models.Model):
    name = models.CharField(max_length=30)
    text = models.TextField()
    tags = GenericRelation('Tag')

    class Meta:
        db_table = 'CaseSensitive_Post'


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class ReporterProxy(Reporter):
    class Meta:
        proxy = True


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter, models.CASCADE)
    reporter_proxy = models.ForeignKey(
        ReporterProxy,
        models.SET_NULL,
        null=True,
        related_name='reporter_proxy',
    )

    def __str__(self):
        return self.headline


class Item(models.Model):
    name = models.CharField(max_length=30)
    date = models.DateField()
    time = models.TimeField()
    last_modified = models.DateTimeField()

    def __str__(self):
        return self.name


class Object(models.Model):
    related_objects = models.ManyToManyField("self", db_constraint=False, symmetrical=False)
    obj_ref = models.ForeignKey('ObjectReference', models.CASCADE, null=True)

    def __str__(self):
        return str(self.id)


class ObjectReference(models.Model):
    obj = models.ForeignKey(Object, models.CASCADE, db_constraint=False)

    def __str__(self):
        return str(self.obj_id)


class ObjectSelfReference(models.Model):
    key = models.CharField(max_length=3, unique=True)
    obj = models.ForeignKey('ObjectSelfReference', models.SET_NULL, null=True)


class CircularA(models.Model):
    key = models.CharField(max_length=3, unique=True)
    obj = models.ForeignKey('CircularB', models.SET_NULL, null=True)

    def natural_key(self):
        return (self.key,)


class CircularB(models.Model):
    key = models.CharField(max_length=3, unique=True)
    obj = models.ForeignKey('CircularA', models.SET_NULL, null=True)

    def natural_key(self):
        return (self.key,)


class RawData(models.Model):
    raw_data = models.BinaryField()


class Author(models.Model):
    name = models.CharField(max_length=255, unique=True)


class Book(models.Model):
    author = models.ForeignKey(Author, models.CASCADE, to_field='name')


class SQLKeywordsModel(models.Model):
    id = models.AutoField(primary_key=True, db_column='select')
    reporter = models.ForeignKey(Reporter, models.CASCADE, db_column='where')

    class Meta:
        db_table = 'order'

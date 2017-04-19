import uuid

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query import ModelIterable, QuerySet
from django.utils.functional import cached_property


# Basic tests

class Author(models.Model):
    name = models.CharField(max_length=50, unique=True)
    first_book = models.ForeignKey('Book', models.CASCADE, related_name='first_time_authors')
    favorite_authors = models.ManyToManyField(
        'self', through='FavoriteAuthors', symmetrical=False, related_name='favors_me')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class AuthorWithAge(Author):
    author = models.OneToOneField(Author, models.CASCADE, parent_link=True)
    age = models.IntegerField()


class FavoriteAuthors(models.Model):
    author = models.ForeignKey(Author, models.CASCADE, to_field='name', related_name='i_like')
    likes_author = models.ForeignKey(Author, models.CASCADE, to_field='name', related_name='likes_me')

    class Meta:
        ordering = ['id']


class AuthorAddress(models.Model):
    author = models.ForeignKey(Author, models.CASCADE, to_field='name', related_name='addresses')
    address = models.TextField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.address


class Book(models.Model):
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(Author, related_name='books')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['id']


class BookWithYear(Book):
    book = models.OneToOneField(Book, models.CASCADE, parent_link=True)
    published_year = models.IntegerField()
    aged_authors = models.ManyToManyField(
        AuthorWithAge, related_name='books_with_year')


class Bio(models.Model):
    author = models.OneToOneField(Author, models.CASCADE)
    books = models.ManyToManyField(Book, blank=True)


class Reader(models.Model):
    name = models.CharField(max_length=50)
    books_read = models.ManyToManyField(Book, related_name='read_by')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class BookReview(models.Model):
    book = models.ForeignKey(BookWithYear, models.CASCADE)
    notes = models.TextField(null=True, blank=True)


# Models for default manager tests

class Qualification(models.Model):
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ['id']


class ModelIterableSubclass(ModelIterable):
    pass


class TeacherQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._iterable_class = ModelIterableSubclass


class TeacherManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('qualifications')


class Teacher(models.Model):
    name = models.CharField(max_length=50)
    qualifications = models.ManyToManyField(Qualification)

    objects = TeacherManager()
    objects_custom = TeacherQuerySet.as_manager()

    def __str__(self):
        return "%s (%s)" % (self.name, ", ".join(q.name for q in self.qualifications.all()))

    class Meta:
        ordering = ['id']


class Department(models.Model):
    name = models.CharField(max_length=50)
    teachers = models.ManyToManyField(Teacher)

    class Meta:
        ordering = ['id']


# GenericRelation/GenericForeignKey tests

class TaggedItem(models.Model):
    tag = models.SlugField()
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        related_name="taggeditem_set2",
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_by_ct = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        null=True,
        related_name='taggeditem_set3',
    )
    created_by_fkey = models.PositiveIntegerField(null=True)
    created_by = GenericForeignKey('created_by_ct', 'created_by_fkey',)
    favorite_ct = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        null=True,
        related_name='taggeditem_set4',
    )
    favorite_fkey = models.CharField(max_length=64, null=True)
    favorite = GenericForeignKey('favorite_ct', 'favorite_fkey')

    def __str__(self):
        return self.tag

    class Meta:
        ordering = ['id']


class Bookmark(models.Model):
    url = models.URLField()
    tags = GenericRelation(TaggedItem, related_query_name='bookmarks')
    favorite_tags = GenericRelation(TaggedItem,
                                    content_type_field='favorite_ct',
                                    object_id_field='favorite_fkey',
                                    related_query_name='favorite_bookmarks')

    class Meta:
        ordering = ['id']


class Comment(models.Model):
    comment = models.TextField()

    # Content-object field
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_pk = models.TextField()
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    class Meta:
        ordering = ['id']


# Models for lookup ordering tests

class House(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    owner = models.ForeignKey('Person', models.SET_NULL, null=True)
    main_room = models.OneToOneField('Room', models.SET_NULL, related_name='main_room_of', null=True)

    class Meta:
        ordering = ['id']


class Room(models.Model):
    name = models.CharField(max_length=50)
    house = models.ForeignKey(House, models.CASCADE, related_name='rooms')

    class Meta:
        ordering = ['id']


class Person(models.Model):
    name = models.CharField(max_length=50)
    houses = models.ManyToManyField(House, related_name='occupants')

    @property
    def primary_house(self):
        # Assume business logic forces every person to have at least one house.
        return sorted(self.houses.all(), key=lambda house: -house.rooms.count())[0]

    @property
    def all_houses(self):
        return list(self.houses.all())

    @cached_property
    def cached_all_houses(self):
        return self.all_houses

    class Meta:
        ordering = ['id']


# Models for nullable FK tests

class Employee(models.Model):
    name = models.CharField(max_length=50)
    boss = models.ForeignKey('self', models.SET_NULL, null=True, related_name='serfs')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


# Ticket #19607

class LessonEntry(models.Model):
    name1 = models.CharField(max_length=200)
    name2 = models.CharField(max_length=200)

    def __str__(self):
        return "%s %s" % (self.name1, self.name2)


class WordEntry(models.Model):
    lesson_entry = models.ForeignKey(LessonEntry, models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return "%s (%s)" % (self.name, self.id)


# Ticket #21410: Regression when related_name="+"

class Author2(models.Model):
    name = models.CharField(max_length=50, unique=True)
    first_book = models.ForeignKey('Book', models.CASCADE, related_name='first_time_authors+')
    favorite_books = models.ManyToManyField('Book', related_name='+')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


# Models for many-to-many with UUID pk test:

class Pet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=20)
    people = models.ManyToManyField(Person, related_name='pets')


class Flea(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_room = models.ForeignKey(Room, models.SET_NULL, related_name='fleas', null=True)
    pets_visited = models.ManyToManyField(Pet, related_name='fleas_hosted')
    people_visited = models.ManyToManyField(Person, related_name='fleas_hosted')

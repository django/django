from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=50, unique=True)
    favorite_books = models.ManyToManyField(
        'Book',
        related_name='preferred_by_authors',
        related_query_name='preferred_by_authors',
    )
    content_type = models.ForeignKey(ContentType, models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey()

    def __str__(self):
        return self.name


class Editor(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Book(models.Model):
    AVAILABLE = 'available'
    RESERVED = 'reserved'
    RENTED = 'rented'
    STATES = (
        (AVAILABLE, 'Available'),
        (RESERVED, 'reserved'),
        (RENTED, 'Rented'),
    )
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        Author,
        models.CASCADE,
        related_name='books',
        related_query_name='book',
    )
    editor = models.ForeignKey(Editor, models.CASCADE)
    generic_author = GenericRelation(Author)
    state = models.CharField(max_length=9, choices=STATES, default=AVAILABLE)

    def __str__(self):
        return self.title


class Borrower(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Reservation(models.Model):
    NEW = 'new'
    STOPPED = 'stopped'
    STATES = (
        (NEW, 'New'),
        (STOPPED, 'Stopped'),
    )
    borrower = models.ForeignKey(
        Borrower,
        models.CASCADE,
        related_name='reservations',
        related_query_name='reservation',
    )
    book = models.ForeignKey(
        Book,
        models.CASCADE,
        related_name='reservations',
        related_query_name='reservation',
    )
    state = models.CharField(max_length=7, choices=STATES, default=NEW)

    def __str__(self):
        return '-'.join((self.book.name, self.borrower.name, self.state))


class RentalSession(models.Model):
    NEW = 'new'
    STOPPED = 'stopped'
    STATES = (
        (NEW, 'New'),
        (STOPPED, 'Stopped'),
    )
    borrower = models.ForeignKey(
        Borrower,
        models.CASCADE,
        related_name='rental_sessions',
        related_query_name='rental_session',
    )
    book = models.ForeignKey(
        Book,
        models.CASCADE,
        related_name='rental_sessions',
        related_query_name='rental_session',
    )
    state = models.CharField(max_length=7, choices=STATES, default=NEW)

    def __str__(self):
        return '-'.join((self.book.name, self.borrower.name, self.state))

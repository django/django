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


class Editor(models.Model):
    name = models.CharField(max_length=255)


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


class Borrower(models.Model):
    name = models.CharField(max_length=50, unique=True)


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


class Seller(models.Model):
    name = models.CharField(max_length=255)


class Currency(models.Model):
    currency = models.CharField(max_length=3)


class ExchangeRate(models.Model):
    rate_date = models.DateField()
    from_currency = models.ForeignKey(
        Currency,
        models.CASCADE,
        related_name='rates_from',
    )
    to_currency = models.ForeignKey(
        Currency,
        models.CASCADE,
        related_name='rates_to',
    )
    rate = models.DecimalField(max_digits=6, decimal_places=4)


class BookDailySales(models.Model):
    book = models.ForeignKey(Book, models.CASCADE, related_name='daily_sales')
    sale_date = models.DateField()
    currency = models.ForeignKey(Currency, models.CASCADE)
    seller = models.ForeignKey(Seller, models.CASCADE)
    sales = models.DecimalField(max_digits=10, decimal_places=2)

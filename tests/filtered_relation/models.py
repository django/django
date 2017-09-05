from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=50, unique=True)
    favourite_books = models.ManyToManyField(
        'Book',
        related_name='preferred_by_authors',
        related_query_name='preferred_by_authors',
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Editor(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Book(models.Model):
    AVAILABLE = 'available'
    RESERVED = 'reserved'
    RENTED = 'rented'
    STATES = [
        (AVAILABLE, 'Available'),
        (RESERVED, 'reserved'),
        (RENTED, 'Rented'),
    ]
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        Author,
        related_name='books',
        related_query_name='book',
        on_delete=models.CASCADE,
    )
    editor = models.ForeignKey(Editor, on_delete=models.CASCADE)
    state = models.CharField(max_length=9, choices=STATES, default=AVAILABLE)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.title


class Borrower(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Reservation(models.Model):
    NEW = 'new'
    STOPPED = 'stopped'
    STATES = [(NEW, 'New'),
              (STOPPED, 'Stopped')]
    borrower = models.ForeignKey(
        Borrower,
        related_name='reservations',
        related_query_name='reservation',
        on_delete=models.CASCADE,
    )
    book = models.ForeignKey(
        Book,
        related_name='reservations',
        related_query_name='reservation',
        on_delete=models.CASCADE,
    )
    state = models.CharField(max_length=7, choices=STATES, default=NEW)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return '-'.join(self.book.name, self.borrower.name, self.state)


class RentalSession(models.Model):
    NEW = 'new'
    STOPPED = 'stopped'
    STATES = [(NEW, 'New'),
              (STOPPED, 'Stopped')]
    borrower = models.ForeignKey(
        Borrower,
        related_name='rental_sessions',
        related_query_name='rental_session',
        on_delete=models.CASCADE,
    )
    book = models.ForeignKey(
        Book,
        related_name='rental_sessions',
        related_query_name='rental_session',
        on_delete=models.CASCADE,
    )
    state = models.CharField(max_length=7, choices=STATES, default=NEW)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return '-'.join(self.book.name, self.borrower.name, self.state)

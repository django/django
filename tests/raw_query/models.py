from django.db import models


class Author(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    dob = models.DateField()

    def __init__(self, *args, **kwargs):
        super(Author, self).__init__(*args, **kwargs)
        # Protect against annotations being passed to __init__ --
        # this'll make the test suite get angry if annotations aren't
        # treated differently than fields.
        for k in kwargs:
            assert k in [f.attname for f in self._meta.fields], \
                "Author.__init__ got an unexpected parameter: %s" % k

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author)
    paperback = models.BooleanField(default=False)
    opening_line = models.TextField()

class Coffee(models.Model):
    brand = models.CharField(max_length=255, db_column="name")

class Reviewer(models.Model):
    reviewed = models.ManyToManyField(Book)

class FriendlyAuthor(Author):
    pass

from django.db import models


class Author(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    dob = models.DateField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Protect against annotations being passed to __init__ --
        # this'll make the test suite get angry if annotations aren't
        # treated differently than fields.
        for k in kwargs:
            assert k in [f.attname for f in self._meta.fields], \
                "Author.__init__ got an unexpected parameter: %s" % k


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, models.CASCADE)
    paperback = models.BooleanField(default=False)
    opening_line = models.TextField()


class BookFkAsPk(models.Model):
    book = models.ForeignKey(Book, models.CASCADE, primary_key=True, db_column="not_the_default")


class Coffee(models.Model):
    brand = models.CharField(max_length=255, db_column="name")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class MixedCaseIDColumn(models.Model):
    id = models.AutoField(primary_key=True, db_column='MiXeD_CaSe_Id')


class Reviewer(models.Model):
    reviewed = models.ManyToManyField(Book)


class FriendlyAuthor(Author):
    pass

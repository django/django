from django.db import models
from django.test import TestCase


class TOAuthor(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]


class TOBook(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(TOAuthor, on_delete=models.CASCADE)
    publication_date = models.DateField()
    isbn = models.CharField(max_length=13, unique=True)

    class Meta:
        unique_together = [["title", "author"]]


class TotallyOrderedTests(TestCase):
    def test_basic_ordering(self):
        self.assertIs(TOAuthor.objects.all().totally_ordered, False)
        self.assertIs(TOAuthor.objects.order_by("pk").totally_ordered, True)
        self.assertIs(TOBook.objects.order_by("isbn").totally_ordered, True)

    def test_composite_constraints(self):
        self.assertIs(
            TOBook.objects.order_by("title", "author_id").totally_ordered, True
        )
        self.assertIs(TOBook.objects.order_by("title").totally_ordered, False)

    def test_reverse_ordering(self):
        self.assertIs(TOAuthor.objects.order_by("-pk").totally_ordered, True)
        self.assertIs(TOBook.objects.order_by("-isbn").totally_ordered, True)

    def test_f_expressions(self):
        self.assertIs(TOAuthor.objects.order_by(models.F("pk")).totally_ordered, True)
        self.assertIs(
            TOAuthor.objects.order_by(models.F("name")).totally_ordered, False
        )

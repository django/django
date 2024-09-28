"""
Specifying ordering

Specify default ordering for a model using the ``ordering`` attribute, which
should be a list or tuple of field names. This tells Django how to order
``QuerySet`` results.

If a field name in ``ordering`` starts with a hyphen, that field will be
ordered in descending order. Otherwise, it'll be ordered in ascending order.
The special-case field name ``"?"`` specifies random order.

The ordering attribute is not required. If you leave it off, ordering will be
undefined -- not random, just undefined.
"""

from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=63, null=True, blank=True)
    editor = models.ForeignKey("self", models.CASCADE, null=True)

    class Meta:
        ordering = ("-pk",)


class Article(models.Model):
    author = models.ForeignKey(Author, models.SET_NULL, null=True)
    second_author = models.ForeignKey(
        Author, models.SET_NULL, null=True, related_name="+"
    )
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    class Meta:
        ordering = (
            "-pub_date",
            models.F("headline"),
            models.F("author__name").asc(),
            models.OrderBy(models.F("second_author__name")),
        )


class OrderedByAuthorArticle(Article):
    class Meta:
        proxy = True
        ordering = ("author", "second_author")


class OrderedByFArticle(Article):
    class Meta:
        proxy = True
        ordering = (models.F("author").asc(nulls_first=True), "id")


class ChildArticle(Article):
    pass


class Reference(models.Model):
    article = models.ForeignKey(OrderedByAuthorArticle, models.CASCADE)

    class Meta:
        ordering = ("article",)


class OrderedByExpression(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        ordering = [models.functions.Lower("name")]


class OrderedByExpressionChild(models.Model):
    parent = models.ForeignKey(OrderedByExpression, models.CASCADE)

    class Meta:
        ordering = ["parent"]


class OrderedByExpressionGrandChild(models.Model):
    parent = models.ForeignKey(OrderedByExpressionChild, models.CASCADE)

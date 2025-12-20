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
from django.db.models import ExpressionWrapper
from django.db.models.expressions import OrderBy
from django.db.models.functions import Lower


class Author(models.Model):
    name = models.CharField(max_length=63, null=True, blank=True)

    class Meta:
        ordering = ('-pk',)


class Article(models.Model):
    author = models.ForeignKey(Author, models.SET_NULL, null=True)
    second_author = models.ForeignKey(Author, models.SET_NULL, null=True, related_name='+')
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    class Meta:
        ordering = (
            '-pub_date',
            'headline',
            models.F('author__name').asc(),
            OrderBy(models.F('second_author__name')),
        )

    def __str__(self):
        return self.headline


class OrderedByAuthorArticle(Article):
    class Meta:
        proxy = True
        ordering = ('author', 'second_author')


class OrderedByFArticle(Article):
    class Meta:
        proxy = True
        ordering = (models.F('author').asc(nulls_first=True), 'id')


class Reference(models.Model):
    article = models.ForeignKey(OrderedByAuthorArticle, models.CASCADE)

    class Meta:
        ordering = ('article',)


class MTIParent(models.Model):
    name = models.CharField(max_length=50)


class MTIChild(MTIParent):
    alias = models.CharField(max_length=50)

    class Meta:
        ordering = (Lower('alias'),)

    def __str__(self):
        return self.alias


class MixedOrderingParent(models.Model):
    title = models.CharField(max_length=50)


class MixedOrderingChild(MixedOrderingParent):
    code = models.CharField(max_length=10)
    alias = models.CharField(max_length=50)
    alt_alias = models.CharField(max_length=50)

    class Meta:
        ordering = (
            'code',
            Lower('alias'),
            OrderBy(
                ExpressionWrapper(
                    Lower('alt_alias'),
                    output_field=models.CharField(),
                ),
                descending=True,
            ),
            Lower('pk'),
        )

    def __str__(self):
        return self.alias

"""
The lookup API

This demonstrates features of the database API.
"""

from django.db import models
from django.db.models.lookups import IsNull


class Alarm(models.Model):
    desc = models.CharField(max_length=100)
    time = models.TimeField()

    def __str__(self):
        return "%s (%s)" % (self.time, self.desc)


class Author(models.Model):
    name = models.CharField(max_length=100)
    alias = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ("name",)


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    author = models.ForeignKey(Author, models.SET_NULL, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
        ordering = ("-pub_date", "headline")

    def __str__(self):
        return self.headline


class Tag(models.Model):
    articles = models.ManyToManyField(Article)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ("name",)


class NulledTextField(models.TextField):
    def get_prep_value(self, value):
        return None if value == "" else value


class NullField(models.Field):
    pass


NullField.register_lookup(IsNull)


@NulledTextField.register_lookup
class NulledTransform(models.Transform):
    lookup_name = "nulled"
    template = "NULL"

    @property
    def output_field(self):
        return NullField()


@NulledTextField.register_lookup
class IsNullWithNoneAsRHS(IsNull):
    lookup_name = "isnull_none_rhs"
    can_use_none_as_rhs = True


class Season(models.Model):
    year = models.PositiveSmallIntegerField()
    gt = models.IntegerField(null=True, blank=True)
    nulled_text_field = NulledTextField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["year"], name="season_year_unique"),
        ]

    def __str__(self):
        return str(self.year)


class Game(models.Model):
    season = models.ForeignKey(Season, models.CASCADE, related_name="games")
    home = models.CharField(max_length=100)
    away = models.CharField(max_length=100)


class Player(models.Model):
    name = models.CharField(max_length=100)
    games = models.ManyToManyField(Game, related_name="players")


class Product(models.Model):
    name = models.CharField(max_length=80)
    qty_target = models.DecimalField(max_digits=6, decimal_places=2)


class Stock(models.Model):
    product = models.ForeignKey(Product, models.CASCADE)
    short = models.BooleanField(default=False)
    qty_available = models.DecimalField(max_digits=6, decimal_places=2)


class Freebie(models.Model):
    gift_product = models.ForeignKey(Product, models.CASCADE)
    stock_id = models.IntegerField(blank=True, null=True)

    stock = models.ForeignObject(
        Stock,
        from_fields=["stock_id", "gift_product"],
        to_fields=["id", "product"],
        on_delete=models.CASCADE,
    )

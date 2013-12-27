from django.apps.registry import Apps
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

# Because we want to test creation and deletion of these as separate things,
# these models are all inserted into a separate Apps so the main test
# runner doesn't migrate them.

new_apps = Apps()


class Author(models.Model):
    name = models.CharField(max_length=255)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        apps = new_apps


class AuthorWithM2M(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        apps = new_apps


class Book(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    # tags = models.ManyToManyField("Tag", related_name="books")

    class Meta:
        apps = new_apps


class BookWithM2M(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    tags = models.ManyToManyField("TagM2MTest", related_name="books")

    class Meta:
        apps = new_apps


class BookWithSlug(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    slug = models.CharField(max_length=20, unique=True)

    class Meta:
        apps = new_apps
        db_table = "schema_book"


class Tag(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    class Meta:
        apps = new_apps


class TagM2MTest(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    class Meta:
        apps = new_apps


class TagIndexed(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    class Meta:
        apps = new_apps
        index_together = [["slug", "title"]]


class TagUniqueRename(models.Model):
    title = models.CharField(max_length=255)
    slug2 = models.SlugField(unique=True)

    class Meta:
        apps = new_apps
        db_table = "schema_tag"


class UniqueTest(models.Model):
    year = models.IntegerField()
    slug = models.SlugField(unique=False)

    class Meta:
        apps = new_apps
        unique_together = ["year", "slug"]


class BookWithLongName(models.Model):
    author_foreign_key_with_really_long_field_name = models.ForeignKey(Author)

    class Meta:
        apps = new_apps


# Based on tests/reserved_names/models.py
@python_2_unicode_compatible
class Thing(models.Model):
    when = models.CharField(max_length=1, primary_key=True)

    class Meta:
        db_table = 'drop'

    def __str__(self):
        return self.when

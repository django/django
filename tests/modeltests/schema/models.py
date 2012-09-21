from django.db import models

# Because we want to test creation and deletion of these as separate things,
# these models are all marked as unmanaged and only marked as managed while
# a schema test is running.


class Author(models.Model):
    name = models.CharField(max_length=255)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        auto_register = False


class AuthorWithM2M(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        auto_register = False


class Book(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    #tags = models.ManyToManyField("Tag", related_name="books")

    class Meta:
        auto_register = False


class BookWithM2M(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    tags = models.ManyToManyField("Tag", related_name="books")

    class Meta:
        auto_register = False


class BookWithSlug(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    slug = models.CharField(max_length=20, unique=True)

    class Meta:
        auto_register = False
        db_table = "schema_book"


class Tag(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    class Meta:
        auto_register = False


class TagUniqueRename(models.Model):
    title = models.CharField(max_length=255)
    slug2 = models.SlugField(unique=True)

    class Meta:
        auto_register = False
        db_table = "schema_tag"


class UniqueTest(models.Model):
    year = models.IntegerField()
    slug = models.SlugField(unique=False)

    class Meta:
        auto_register = False
        unique_together = ["year", "slug"]

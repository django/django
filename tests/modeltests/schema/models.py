from django.db import models

# Because we want to test creation and deletion of these as separate things,
# these models are all marked as unmanaged and only marked as managed while
# a schema test is running.


class Author(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        managed = False


class AuthorWithM2M(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        managed = False


class Book(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    #tags = models.ManyToManyField("Tag", related_name="books")

    class Meta:
        managed = False


class Tag(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    class Meta:
        managed = False


class TagUniqueRename(models.Model):
    title = models.CharField(max_length=255)
    slug2 = models.SlugField(unique=True)

    class Meta:
        managed = False
        db_table = "schema_tag"


class UniqueTest(models.Model):
    year = models.IntegerField()
    slug = models.SlugField(unique=False)

    class Meta:
        managed = False
        unique_together = ["year", "slug"]

from django.apps.registry import Apps
from django.db import models

# Because we want to test creation and deletion of these as separate things,
# these models are all inserted into a separate Apps so the main test
# runner doesn't migrate them.

new_apps = Apps()


class Author(models.Model):
    name = models.CharField(max_length=255)
    height = models.PositiveIntegerField(null=True, blank=True)
    weight = models.IntegerField(null=True, blank=True)
    uuid = models.UUIDField(null=True)

    class Meta:
        apps = new_apps


class AuthorCharFieldWithIndex(models.Model):
    char_field = models.CharField(max_length=31, db_index=True)

    class Meta:
        apps = new_apps


class AuthorTextFieldWithIndex(models.Model):
    text_field = models.TextField(db_index=True)

    class Meta:
        apps = new_apps


class AuthorWithDefaultHeight(models.Model):
    name = models.CharField(max_length=255)
    height = models.PositiveIntegerField(null=True, blank=True, default=42)

    class Meta:
        apps = new_apps


class AuthorWithEvenLongerName(models.Model):
    name = models.CharField(max_length=255)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        apps = new_apps


class AuthorWithIndexedName(models.Model):
    name = models.CharField(max_length=255, db_index=True)

    class Meta:
        apps = new_apps


class AuthorWithUniqueName(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        apps = new_apps


class AuthorWithIndexedNameAndBirthday(models.Model):
    name = models.CharField(max_length=255)
    birthday = models.DateField()

    class Meta:
        apps = new_apps
        index_together = [['name', 'birthday']]


class AuthorWithUniqueNameAndBirthday(models.Model):
    name = models.CharField(max_length=255)
    birthday = models.DateField()

    class Meta:
        apps = new_apps
        unique_together = [['name', 'birthday']]


class Book(models.Model):
    author = models.ForeignKey(Author, models.CASCADE)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    # tags = models.ManyToManyField("Tag", related_name="books")

    class Meta:
        apps = new_apps


class BookWeak(models.Model):
    author = models.ForeignKey(Author, models.CASCADE, db_constraint=False)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()

    class Meta:
        apps = new_apps


class BookWithLongName(models.Model):
    author_foreign_key_with_really_long_field_name = models.ForeignKey(
        AuthorWithEvenLongerName,
        models.CASCADE,
    )

    class Meta:
        apps = new_apps


class BookWithO2O(models.Model):
    author = models.OneToOneField(Author, models.CASCADE)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()

    class Meta:
        apps = new_apps
        db_table = "schema_book"


class BookWithSlug(models.Model):
    author = models.ForeignKey(Author, models.CASCADE)
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()
    slug = models.CharField(max_length=20, unique=True)

    class Meta:
        apps = new_apps
        db_table = "schema_book"


class BookWithoutAuthor(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    pub_date = models.DateTimeField()

    class Meta:
        apps = new_apps
        db_table = "schema_book"


class BookForeignObj(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    author_id = models.IntegerField()

    class Meta:
        apps = new_apps


class IntegerPK(models.Model):
    i = models.IntegerField(primary_key=True)
    j = models.IntegerField(unique=True)

    class Meta:
        apps = new_apps
        db_table = "INTEGERPK"  # uppercase to ensure proper quoting


class Note(models.Model):
    info = models.TextField()

    class Meta:
        apps = new_apps


class NoteRename(models.Model):
    detail_info = models.TextField()

    class Meta:
        apps = new_apps
        db_table = "schema_note"


class Tag(models.Model):
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


class TagM2MTest(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    class Meta:
        apps = new_apps


class TagUniqueRename(models.Model):
    title = models.CharField(max_length=255)
    slug2 = models.SlugField(unique=True)

    class Meta:
        apps = new_apps
        db_table = "schema_tag"


# Based on tests/reserved_names/models.py
class Thing(models.Model):
    when = models.CharField(max_length=1, primary_key=True)

    class Meta:
        apps = new_apps
        db_table = 'drop'

    def __str__(self):
        return self.when


class UniqueTest(models.Model):
    year = models.IntegerField()
    slug = models.SlugField(unique=False)

    class Meta:
        apps = new_apps
        unique_together = ["year", "slug"]


class Node(models.Model):
    node_id = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', models.CASCADE, null=True, blank=True)

    class Meta:
        apps = new_apps

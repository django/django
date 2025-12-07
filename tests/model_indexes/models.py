from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.CharField(max_length=50)
    pages = models.IntegerField(db_column="page_count")
    shortcut = models.CharField(max_length=50, db_tablespace="idx_tbls")
    isbn = models.CharField(max_length=50, db_tablespace="idx_tbls")
    barcode = models.CharField(max_length=31)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["isbn", "id"]),
            models.Index(
                fields=["barcode"], name="%(app_label)s_%(class)s_barcode_idx"
            ),
        ]


class AbstractModel(models.Model):
    name = models.CharField(max_length=50)
    shortcut = models.CharField(max_length=3)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["shortcut"], name="%(app_label)s_%(class)s_idx"),
        ]


class ChildModel1(AbstractModel):
    pass


class ChildModel2(AbstractModel):
    pass

from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.CharField(max_length=50)
    pages = models.IntegerField(db_column='page_count')
    shortcut = models.CharField(max_length=50, db_tablespace='idx_tbls')
    isbn = models.CharField(max_length=50, db_tablespace='idx_tbls')

    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['isbn', 'id']),
        ]


class AbstractModel(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        abstract = True
        indexes = [models.Index(fields=['name'])]


class ChildModel1(AbstractModel):
    pass


class ChildModel2(AbstractModel):
    pass

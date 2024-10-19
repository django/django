"""
Many-to-many relationships

To define a many-to-many relationship, use ``ManyToManyField()``.

In this example, an ``Article`` can be published in multiple ``Publication``
objects, and a ``Publication`` has multiple ``Article`` objects.
"""

from django.db import models


class Publication(models.Model):
    title = models.CharField(max_length=30)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class NoDeletedArticleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(headline="deleted")


class Article(models.Model):
    headline = models.CharField(max_length=100)
    # Assign a string as name to make sure the intermediary model is
    # correctly created. Refs #20207
    publications = models.ManyToManyField(Publication, name="publications")
    tags = models.ManyToManyField(Tag, related_name="tags")
    authors = models.ManyToManyField("User", through="UserArticle")

    objects = NoDeletedArticleManager()

    class Meta:
        ordering = ("headline",)

    def __str__(self):
        return self.headline


class User(models.Model):
    username = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.username


class UserArticle(models.Model):
    user = models.ForeignKey(User, models.CASCADE, to_field="username")
    article = models.ForeignKey(Article, models.CASCADE)


# Models to test correct related_name inheritance
class AbstractArticle(models.Model):
    class Meta:
        abstract = True

    publications = models.ManyToManyField(
        Publication, name="publications", related_name="+"
    )


class InheritedArticleA(AbstractArticle):
    pass


class InheritedArticleB(AbstractArticle):
    pass


class NullableTargetArticle(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(
        Publication, through="NullablePublicationThrough"
    )


class NullablePublicationThrough(models.Model):
    article = models.ForeignKey(NullableTargetArticle, models.CASCADE)
    publication = models.ForeignKey(Publication, models.CASCADE, null=True)

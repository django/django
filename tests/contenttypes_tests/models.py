from urllib.parse import quote

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import SiteManager
from django.db import models


class Site(models.Model):
    domain = models.CharField(max_length=100)
    objects = SiteManager()

    def __str__(self):
        return self.domain


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return '/authors/%s/' % self.id


class Article(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField()
    author = models.ForeignKey(Author, models.CASCADE)
    date_created = models.DateTimeField()

    def __str__(self):
        return self.title


class SchemeIncludedURL(models.Model):
    url = models.URLField(max_length=100)

    def __str__(self):
        return self.url

    def get_absolute_url(self):
        return self.url


class ConcreteModel(models.Model):
    name = models.CharField(max_length=10)


class ProxyModel(ConcreteModel):
    class Meta:
        proxy = True


class FooWithoutUrl(models.Model):
    """
    Fake model not defining ``get_absolute_url`` for
    ContentTypesTests.test_shortcut_view_without_get_absolute_url()
    """
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class FooWithUrl(FooWithoutUrl):
    """
    Fake model defining ``get_absolute_url`` for
    ContentTypesTests.test_shortcut_view().
    """

    def get_absolute_url(self):
        return "/users/%s/" % quote(self.name)


class FooWithBrokenAbsoluteUrl(FooWithoutUrl):
    """
    Fake model defining a ``get_absolute_url`` method containing an error
    """

    def get_absolute_url(self):
        return "/users/%s/" % self.unknown_field


class Question(models.Model):
    text = models.CharField(max_length=200)
    answer_set = GenericRelation('Answer')


class Answer(models.Model):
    text = models.CharField(max_length=200)
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    question = GenericForeignKey()

    class Meta:
        order_with_respect_to = 'question'

    def __str__(self):
        return self.text


class Post(models.Model):
    """An ordered tag on an item."""
    title = models.CharField(max_length=200)
    content_type = models.ForeignKey(ContentType, models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    parent = GenericForeignKey()
    children = GenericRelation('Post')

    class Meta:
        order_with_respect_to = 'parent'

    def __str__(self):
        return self.title


class ModelWithNullFKToSite(models.Model):
    title = models.CharField(max_length=200)
    site = models.ForeignKey(Site, null=True, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return '/title/%s/' % quote(self.title)

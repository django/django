from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.http import urlquote


class ConcreteModel(models.Model):
    name = models.CharField(max_length=10)


class ProxyModel(ConcreteModel):
    class Meta:
        proxy = True


@python_2_unicode_compatible
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
        return "/users/%s/" % urlquote(self.name)


class FooWithBrokenAbsoluteUrl(FooWithoutUrl):
    """
    Fake model defining a ``get_absolute_url`` method containing an error
    """

    def get_absolute_url(self):
        return "/users/%s/" % self.unknown_field

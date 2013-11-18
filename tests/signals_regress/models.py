from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.dispatch import receiver

@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=20)
    authors = models.ManyToManyField(Author)

    def __str__(self):
        return self.name

@receiver(models.signals.class_prepared)
# exists because tests.SignalsRegressTests.setUp() connects *after* signal sends
def class_prepared_receiver(sender, **kwargs):
    sender._meta.class_prepared_signal_fired = True

@python_2_unicode_compatible
class SomethingAbstract(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True

class NotAbstract(SomethingAbstract):
    pass

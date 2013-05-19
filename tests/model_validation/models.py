from django.db import models


class ThingItem(object):

    def __init__(self, value, display):
        self.value = value
        self.display = display

    def __iter__(self):
        return (x for x in [self.value, self.display])

    def __len__(self):
        return 2


class Things(object):

    def __iter__(self):
        return (x for x in [ThingItem(1, 2), ThingItem(3, 4)])


class ThingWithIterableChoices(models.Model):

    # Testing choices= Iterable of Iterables
    #   See: https://code.djangoproject.com/ticket/20430
    thing = models.CharField(max_length=100, blank=True, choices=Things())

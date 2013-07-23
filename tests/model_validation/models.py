from django.db import models


class ThingItem(object):

    def __init__(self, value, display):
        self.value = value
        self.display = display

    def __iter__(self):
        return (x for x in [self.value, self.display])

    def __getitem__(self, key):
        return [self.value, self.display][key]

    def __len__(self):
        return 2


class Things(object):

    def __iter__(self):
        return (x for x in [ThingItem('1', 'One'), ThingItem('2', 'Two')])


class ThingWithIterableChoices(models.Model):

    # Testing choices= Iterable of Iterables
    #   See: https://code.djangoproject.com/ticket/20430
    thing = models.CharField(max_length=100, blank=True, choices=Things())

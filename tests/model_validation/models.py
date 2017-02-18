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

    class Meta:
        # Models created as unmanaged as these aren't ever queried
        managed = False


class ManyToManyRel(models.Model):
    thing1 = models.ManyToManyField(ThingWithIterableChoices, related_name='+')
    thing2 = models.ManyToManyField(ThingWithIterableChoices, related_name='+')

    class Meta:
        # Models created as unmanaged as these aren't ever queried
        managed = False


class FKRel(models.Model):
    thing1 = models.ForeignKey(ThingWithIterableChoices, related_name='+')
    thing2 = models.ForeignKey(ThingWithIterableChoices, related_name='+')

    class Meta:
        # Models created as unmanaged as these aren't ever queried
        managed = False

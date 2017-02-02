from django.db import models


class Event(models.Model):
    # Oracle can have problems with a column named "date"
    date = models.DateField(db_column="event_date")


class Parent(models.Model):
    name = models.CharField(max_length=128)


class Child(models.Model):
    parent = models.ForeignKey(Parent, models.SET_NULL, editable=False, null=True)
    name = models.CharField(max_length=30, blank=True)
    age = models.IntegerField(null=True, blank=True)


class Genre(models.Model):
    name = models.CharField(max_length=20)


class Band(models.Model):
    name = models.CharField(max_length=20)
    nr_of_members = models.PositiveIntegerField()
    genres = models.ManyToManyField(Genre)


class Musician(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(Musician, through='Membership')

    def __str__(self):
        return self.name


class Concert(models.Model):
    name = models.CharField(max_length=30)
    group = models.ForeignKey(Group, models.CASCADE)


class Membership(models.Model):
    music = models.ForeignKey(Musician, models.CASCADE)
    group = models.ForeignKey(Group, models.CASCADE)
    role = models.CharField(max_length=15)


class Quartet(Group):
    pass


class ChordsMusician(Musician):
    pass


class ChordsBand(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(ChordsMusician, through='Invitation')


class Invitation(models.Model):
    player = models.ForeignKey(ChordsMusician, models.CASCADE)
    band = models.ForeignKey(ChordsBand, models.CASCADE)
    instrument = models.CharField(max_length=15)


class Swallow(models.Model):
    origin = models.CharField(max_length=255)
    load = models.FloatField()
    speed = models.FloatField()

    class Meta:
        ordering = ('speed', 'load')


class SwallowOneToOne(models.Model):
    swallow = models.OneToOneField(Swallow, models.CASCADE)


class UnorderedObject(models.Model):
    """
    Model without any defined `Meta.ordering`.
    Refs #17198.
    """
    bool = models.BooleanField(default=True)


class OrderedObjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by('number')


class OrderedObject(models.Model):
    """
    Model with Manager that defines a default order.
    Refs #17198.
    """
    name = models.CharField(max_length=255)
    bool = models.BooleanField(default=True)
    number = models.IntegerField(default=0, db_column='number_val')

    objects = OrderedObjectManager()


class CustomIdUser(models.Model):
    uuid = models.AutoField(primary_key=True)

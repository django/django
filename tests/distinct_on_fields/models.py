from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=10)
    parent = models.ForeignKey(
        'self',
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='children',
    )

    class Meta:
        ordering = ['name']


class Celebrity(models.Model):
    name = models.CharField("Name", max_length=20)
    greatest_fan = models.ForeignKey(
        "Fan",
        models.SET_NULL,
        null=True,
        unique=True,
    )


class Fan(models.Model):
    fan_of = models.ForeignKey(Celebrity, models.CASCADE)


class Staff(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    organisation = models.CharField(max_length=100)
    tags = models.ManyToManyField(Tag, through='StaffTag')
    coworkers = models.ManyToManyField('self')


class StaffTag(models.Model):
    staff = models.ForeignKey(Staff, models.CASCADE)
    tag = models.ForeignKey(Tag, models.CASCADE)

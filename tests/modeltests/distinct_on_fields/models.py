from django.db import models

class Tag(models.Model):
    name = models.CharField(max_length=10)
    parent = models.ForeignKey('self', blank=True, null=True,
            related_name='children')

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

class Celebrity(models.Model):
    name = models.CharField("Name", max_length=20)
    greatest_fan = models.ForeignKey("Fan", null=True, unique=True)

    def __unicode__(self):
        return self.name

class Fan(models.Model):
    fan_of = models.ForeignKey(Celebrity)

class Staff(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    organisation = models.CharField(max_length=100)
    tags = models.ManyToManyField(Tag, through='StaffTag')
    coworkers = models.ManyToManyField('self')

    def __unicode__(self):
        return self.name

class StaffTag(models.Model):
    staff = models.ForeignKey(Staff)
    tag = models.ForeignKey(Tag)

    def __unicode__(self):
        return u"%s -> %s" % (self.tag, self.staff)

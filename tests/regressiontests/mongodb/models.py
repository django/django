from django.db import models


class Artist(models.Model):
    id = models.NativeAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    good = models.BooleanField()
    
    current_group = models.ForeignKey("Group", null=True)
    
    def __unicode__(self):
        return self.name


class Group(models.Model):
    id = models.NativeAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    year_formed = models.IntegerField(null=True)


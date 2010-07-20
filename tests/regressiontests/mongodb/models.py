from django.db import models


class Artist(models.Model):
    id = models.NativeAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    good = models.BooleanField()
    age = models.IntegerField(null=True)
    
    current_group = models.ForeignKey("Group", null=True,
        related_name="current_artists")
    
    def __unicode__(self):
        return self.name


class Group(models.Model):
    id = models.NativeAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    year_formed = models.IntegerField(null=True)


class Post(models.Model):
    id = models.NativeAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    
    tags = models.ListField(
        models.CharField(max_length=255)
    )
    
    magic_numbers = models.ListField(
        models.IntegerField()
    )

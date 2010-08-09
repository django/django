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


class Revision(models.Model):
    number = models.IntegerField()
    content = models.TextField()


class AuthenticatedRevision(Revision):
    # This is a really stupid way to add optional authentication, but it serves
    # its purpose.
    author = models.CharField(max_length=100)


class WikiPage(models.Model):
    id = models.NativeAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    
    revisions = models.ListField(
        models.EmbeddedModel(Revision)
    )

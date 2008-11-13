from django.db import models
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

class Episode(models.Model):
    name = models.CharField(max_length=100)

class Media(models.Model):
    """
    Media that can associated to any object.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    url = models.URLField(verify_exists=False)

    def __unicode__(self):
        return self.url

class MediaInline(generic.GenericTabularInline):
    model = Media
    extra = 1
    
class EpisodeAdmin(admin.ModelAdmin):
    inlines = [
        MediaInline,
    ]

admin.site.register(Episode, EpisodeAdmin)

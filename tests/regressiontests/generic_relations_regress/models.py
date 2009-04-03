from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

class Link(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        return "Link to %s id=%s" % (self.content_type, self.object_id)

class Place(models.Model):
    name = models.CharField(max_length=100)
    links = generic.GenericRelation(Link)
    
    def __unicode__(self):
        return "Place: %s" % self.name
    
class Restaurant(Place): 
    def __unicode__(self):
        return "Restaurant: %s" % self.name
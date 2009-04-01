from django.contrib.gis.db import models
from django.contrib.localflavor.us.models import USStateField

class Location(models.Model):
    point = models.PointField()
    objects = models.GeoManager()
    def __unicode__(self): return self.point.wkt

class City(models.Model):
    name = models.CharField(max_length=50)
    state = USStateField()
    location = models.ForeignKey(Location)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class AugmentedLocation(Location):
    extra_text = models.TextField(blank=True)
    objects = models.GeoManager()
    
class DirectoryEntry(models.Model):
    listing_text = models.CharField(max_length=50)
    location = models.ForeignKey(AugmentedLocation)
    objects = models.GeoManager()

class Parcel(models.Model):
    name = models.CharField(max_length=30)
    city = models.ForeignKey(City)
    center1 = models.PointField()
    # Throwing a curveball w/`db_column` here.
    center2 = models.PointField(srid=2276, db_column='mycenter') 
    border1 = models.PolygonField()
    border2 = models.PolygonField(srid=2276)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

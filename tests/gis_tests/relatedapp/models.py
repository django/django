from django.contrib.gis.db import models
from django.utils.encoding import python_2_unicode_compatible


class SimpleModel(models.Model):

    objects = models.GeoManager()

    class Meta:
        abstract = True


@python_2_unicode_compatible
class Location(SimpleModel):
    point = models.PointField()

    def __str__(self):
        return self.point.wkt


@python_2_unicode_compatible
class City(SimpleModel):
    name = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
    location = models.ForeignKey(Location)

    def __str__(self):
        return self.name


class AugmentedLocation(Location):
    extra_text = models.TextField(blank=True)

    objects = models.GeoManager()


class DirectoryEntry(SimpleModel):
    listing_text = models.CharField(max_length=50)
    location = models.ForeignKey(AugmentedLocation)


@python_2_unicode_compatible
class Parcel(SimpleModel):
    name = models.CharField(max_length=30)
    city = models.ForeignKey(City)
    center1 = models.PointField()
    # Throwing a curveball w/`db_column` here.
    center2 = models.PointField(srid=2276, db_column='mycenter')
    border1 = models.PolygonField()
    border2 = models.PolygonField(srid=2276)

    def __str__(self):
        return self.name


# These use the GeoManager but do not have any geographic fields.
class Author(SimpleModel):
    name = models.CharField(max_length=100)
    dob = models.DateField()


class Article(SimpleModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, unique=True)


class Book(SimpleModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, related_name='books', null=True)


class Event(SimpleModel):
    name = models.CharField(max_length=100)
    when = models.DateTimeField()

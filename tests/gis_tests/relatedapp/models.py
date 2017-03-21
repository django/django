from django.contrib.gis.db import models


class SimpleModel(models.Model):
    class Meta:
        abstract = True
        required_db_features = ['gis_enabled']


class Location(SimpleModel):
    point = models.PointField()

    def __str__(self):
        return self.point.wkt


class City(SimpleModel):
    name = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
    location = models.ForeignKey(Location, models.CASCADE)

    def __str__(self):
        return self.name


class AugmentedLocation(Location):
    extra_text = models.TextField(blank=True)


class DirectoryEntry(SimpleModel):
    listing_text = models.CharField(max_length=50)
    location = models.ForeignKey(AugmentedLocation, models.CASCADE)


class Parcel(SimpleModel):
    name = models.CharField(max_length=30)
    city = models.ForeignKey(City, models.CASCADE)
    center1 = models.PointField()
    # Throwing a curveball w/`db_column` here.
    center2 = models.PointField(srid=2276, db_column='mycenter')
    border1 = models.PolygonField()
    border2 = models.PolygonField(srid=2276)

    def __str__(self):
        return self.name


class Author(SimpleModel):
    name = models.CharField(max_length=100)
    dob = models.DateField()


class Article(SimpleModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, models.CASCADE, unique=True)


class Book(SimpleModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, models.SET_NULL, related_name='books', null=True)


class Event(SimpleModel):
    name = models.CharField(max_length=100)
    when = models.DateTimeField()

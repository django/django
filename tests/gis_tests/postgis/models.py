from django.contrib.gis.db import models
from django.contrib.gis.db.backends.postgis.indexes import GistIndex


class IndexedCountry(models.Model):
    mpoly = models.MultiPolygonField()  # SRID, by default, is 4326

    class Meta:
        app_label = 'geoapp'
        required_db_features = ['gis_enabled']
        indexes = [
            GistIndex(fields=['mpoly']),
        ]

"""
 The GeometryColumns and SpatialRefSys models for the PostGIS backend.
"""
from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
from django.db import models


class PostGISGeometryColumns(models.Model):
    """
    The 'geometry_columns' view from PostGIS. See the PostGIS
    documentation at Ch. 4.3.2.
    """
    f_table_catalog = models.CharField(max_length=256)
    f_table_schema = models.CharField(max_length=256)
    f_table_name = models.CharField(max_length=256)
    f_geometry_column = models.CharField(max_length=256)
    coord_dimension = models.IntegerField()
    srid = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=30)

    class Meta:
        app_label = 'gis'
        db_table = 'geometry_columns'
        managed = False

    @classmethod
    def table_name_col(cls):
        """
        Return the name of the metadata column used to store the feature table
        name.
        """
        return 'f_table_name'

    @classmethod
    def geom_col_name(cls):
        """
        Return the name of the metadata column used to store the feature
        geometry column.
        """
        return 'f_geometry_column'

    def __str__(self):
        return "%s.%s - %dD %s field (SRID: %d)" % \
               (self.f_table_name, self.f_geometry_column,
                self.coord_dimension, self.type, self.srid)


class PostGISSpatialRefSys(models.Model, SpatialRefSysMixin):
    """
    The 'spatial_ref_sys' table from PostGIS. See the PostGIS
    documentation at Ch. 4.2.1.
    """
    srid = models.IntegerField(primary_key=True)
    auth_name = models.CharField(max_length=256)
    auth_srid = models.IntegerField()
    srtext = models.CharField(max_length=2048)
    proj4text = models.CharField(max_length=2048)

    class Meta:
        app_label = 'gis'
        db_table = 'spatial_ref_sys'
        managed = False

    @property
    def wkt(self):
        return self.srtext

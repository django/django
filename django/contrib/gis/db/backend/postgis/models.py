"""
 The GeometryColumns and SpatialRefSys models for the PostGIS backend.
"""
from django.db import models
from django.contrib.gis.models import SpatialRefSysMixin

# Checking for the presence of GDAL (needed for the SpatialReference object)
from django.contrib.gis.gdal import HAS_GDAL
if HAS_GDAL:
    from django.contrib.gis.gdal import SpatialReference

class GeometryColumns(models.Model):
    """
    The 'geometry_columns' table from the PostGIS. See the PostGIS
    documentation at Ch. 4.2.2.
    """
    f_table_catalog = models.CharField(max_length=256)
    f_table_schema = models.CharField(max_length=256)
    f_table_name = models.CharField(max_length=256)
    f_geometry_column = models.CharField(max_length=256)
    coord_dimension = models.IntegerField()
    srid = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=30)

    class Meta:
        db_table = 'geometry_columns'

    @classmethod
    def table_name_col(cls):
        """
        Returns the name of the metadata column used to store the 
        the feature table name.
        """
        return 'f_table_name'

    @classmethod
    def geom_col_name(cls):
        """
        Returns the name of the metadata column used to store the 
        the feature geometry column.
        """
        return 'f_geometry_column'

    def __unicode__(self):
        return "%s.%s - %dD %s field (SRID: %d)" % \
               (self.f_table_name, self.f_geometry_column,
                self.coord_dimension, self.type, self.srid)

class SpatialRefSys(models.Model, SpatialRefSysMixin):
    """
    The 'spatial_ref_sys' table from PostGIS. See the PostGIS
    documentaiton at Ch. 4.2.1.
    """
    srid = models.IntegerField(primary_key=True)
    auth_name = models.CharField(max_length=256)
    auth_srid = models.IntegerField()
    srtext = models.CharField(max_length=2048)
    proj4text = models.CharField(max_length=2048)

    class Meta:
        db_table = 'spatial_ref_sys'

    @property
    def wkt(self):
        return self.srtext

    @classmethod
    def wkt_col(cls):
        return 'srtext'

"""
 The GeometryColumns and SpatialRefSys models for the SpatiaLite backend.
"""
from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class SpatialiteGeometryColumns(models.Model):
    """
    The 'geometry_columns' table from SpatiaLite.
    """
    f_table_name = models.CharField(max_length=256)
    f_geometry_column = models.CharField(max_length=256)
    coord_dimension = models.IntegerField()
    srid = models.IntegerField(primary_key=True)
    spatial_index_enabled = models.IntegerField()
    type = models.IntegerField(db_column='geometry_type')

    class Meta:
        app_label = 'gis'
        db_table = 'geometry_columns'
        managed = False

    @classmethod
    def table_name_col(cls):
        """
        Returns the name of the metadata column used to store the feature table
        name.
        """
        return 'f_table_name'

    @classmethod
    def geom_col_name(cls):
        """
        Returns the name of the metadata column used to store the feature
        geometry column.
        """
        return 'f_geometry_column'

    def __str__(self):
        return "%s.%s - %dD %s field (SRID: %d)" % \
               (self.f_table_name, self.f_geometry_column,
                self.coord_dimension, self.type, self.srid)


class SpatialiteSpatialRefSys(models.Model, SpatialRefSysMixin):
    """
    The 'spatial_ref_sys' table from SpatiaLite.
    """
    srid = models.IntegerField(primary_key=True)
    auth_name = models.CharField(max_length=256)
    auth_srid = models.IntegerField()
    ref_sys_name = models.CharField(max_length=256)
    proj4text = models.CharField(max_length=2048)
    srtext = models.CharField(max_length=2048)

    @property
    def wkt(self):
        return self.srtext

    class Meta:
        app_label = 'gis'
        db_table = 'spatial_ref_sys'
        managed = False

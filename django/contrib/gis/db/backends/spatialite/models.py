"""
 The GeometryColumns and SpatialRefSys models for the SpatiaLite backend.
"""
from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
from django.contrib.gis.db.backends.spatialite.base import DatabaseWrapper
from django.db import connection, models
from django.db.backends.signals import connection_created
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

    @property
    def wkt(self):
        if hasattr(self, 'srtext'):
            return self.srtext
        from django.contrib.gis.gdal import SpatialReference
        return SpatialReference(self.proj4text).wkt

    class Meta:
        app_label = 'gis'
        db_table = 'spatial_ref_sys'
        managed = False


def add_spatial_version_related_fields(sender, **kwargs):
    """
    Adds fields after establishing a database connection to prevent database
    operations at compile time.
    """
    if connection_created.disconnect(add_spatial_version_related_fields, sender=DatabaseWrapper):
        spatial_version = connection.ops.spatial_version[0]
        if spatial_version >= 4:
            SpatialiteSpatialRefSys.add_to_class('srtext', models.CharField(max_length=2048))
            SpatialiteGeometryColumns.add_to_class('type', models.IntegerField(db_column='geometry_type'))
        else:
            SpatialiteGeometryColumns.add_to_class('type', models.CharField(max_length=30))
connection_created.connect(add_spatial_version_related_fields, sender=DatabaseWrapper)

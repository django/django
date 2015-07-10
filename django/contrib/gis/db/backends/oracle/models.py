"""
 The GeometryColumns and SpatialRefSys models for the Oracle spatial
 backend.

 It should be noted that Oracle Spatial does not have database tables
 named according to the OGC standard, so the closest analogs are used.
 For example, the `USER_SDO_GEOM_METADATA` is used for the GeometryColumns
 model and the `SDO_COORD_REF_SYS` is used for the SpatialRefSys model.
"""
from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class OracleGeometryColumns(models.Model):
    "Maps to the Oracle USER_SDO_GEOM_METADATA table."
    table_name = models.CharField(max_length=32)
    column_name = models.CharField(max_length=1024)
    srid = models.IntegerField(primary_key=True)
    # TODO: Add support for `diminfo` column (type MDSYS.SDO_DIM_ARRAY).

    class Meta:
        app_label = 'gis'
        db_table = 'USER_SDO_GEOM_METADATA'
        managed = False

    @classmethod
    def table_name_col(cls):
        """
        Returns the name of the metadata column used to store the feature table
        name.
        """
        return 'table_name'

    @classmethod
    def geom_col_name(cls):
        """
        Returns the name of the metadata column used to store the feature
        geometry column.
        """
        return 'column_name'

    def __str__(self):
        return '%s - %s (SRID: %s)' % (self.table_name, self.column_name, self.srid)


class OracleSpatialRefSys(models.Model, SpatialRefSysMixin):
    "Maps to the Oracle MDSYS.CS_SRS table."
    cs_name = models.CharField(max_length=68)
    srid = models.IntegerField(primary_key=True)
    auth_srid = models.IntegerField()
    auth_name = models.CharField(max_length=256)
    wktext = models.CharField(max_length=2046)
    # Optional geometry representing the bounds of this coordinate
    # system.  By default, all are NULL in the table.
    cs_bounds = models.PolygonField(null=True)
    objects = models.GeoManager()

    class Meta:
        app_label = 'gis'
        db_table = 'CS_SRS'
        managed = False

    @property
    def wkt(self):
        return self.wktext

    @classmethod
    def wkt_col(cls):
        return 'wktext'

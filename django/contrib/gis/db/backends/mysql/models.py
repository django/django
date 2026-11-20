from functools import cached_property

from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
from django.contrib.gis.gdal import SpatialReference
from django.db import models


class GeometryColumnsManager(models.Manager):
    def get_queryset(self):
        # INFORMATION_SCHEMA includes columns from every visible database.
        database = models.Func(function="DATABASE", output_field=models.CharField())
        return super().get_queryset().filter(f_table_schema=database)


class MySQLGeometryColumns(models.Model):
    f_table_schema = models.CharField(db_column="TABLE_SCHEMA", max_length=64)
    f_table_name = models.CharField(db_column="TABLE_NAME", max_length=64)
    f_geometry_column = models.CharField(db_column="COLUMN_NAME", max_length=64)
    pk = models.CompositePrimaryKey(
        "f_table_schema", "f_table_name", "f_geometry_column"
    )
    srid = models.PositiveIntegerField(db_column="SRS_ID", null=True)
    type = models.CharField(db_column="GEOMETRY_TYPE_NAME", max_length=32)

    objects = GeometryColumnsManager()

    class Meta:
        app_label = "gis"
        db_table = "`information_schema`.`ST_GEOMETRY_COLUMNS`"
        managed = False

    @classmethod
    def table_name_col(cls):
        return "f_table_name"

    @classmethod
    def geom_col_name(cls):
        return "f_geometry_column"


class MySQLSpatialRefSys(models.Model, SpatialRefSysMixin):
    srid = models.PositiveIntegerField(db_column="SRS_ID", primary_key=True)
    ref_sys_name = models.CharField(db_column="SRS_NAME", max_length=80)
    auth_name = models.CharField(db_column="ORGANIZATION", max_length=256, null=True)
    auth_srid = models.PositiveIntegerField(
        db_column="ORGANIZATION_COORDSYS_ID", null=True
    )
    wkt = models.TextField(db_column="DEFINITION")

    class Meta:
        app_label = "gis"
        db_table = "`information_schema`.`ST_SPATIAL_REFERENCE_SYSTEMS`"
        managed = False

    @cached_property
    def srs(self):
        return SpatialReference(self.wkt)

# In django/contrib/gis/db/backends/mysql/models.py

from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
from django.db import models


class MySQLGeometryColumns(models.Model):
    """
    Model for MySQL 8's information_schema.st_geometry_columns view.
    Uses TABLE_CATALOG as primary key (always 'def' and unique per row).
    """

    TABLE_CATALOG = models.CharField(
        max_length=64, db_column="TABLE_CATALOG", primary_key=True
    )
    TABLE_SCHEMA = models.CharField(max_length=64, db_column="TABLE_SCHEMA")
    TABLE_NAME = models.CharField(max_length=64, db_column="TABLE_NAME")
    COLUMN_NAME = models.CharField(max_length=64, db_column="COLUMN_NAME")
    SRS_NAME = models.CharField(max_length=80, db_column="SRS_NAME")
    SRS_ID = models.IntegerField(db_column="SRS_ID")
    GEOMETRY_TYPE_NAME = models.CharField(max_length=30, db_column="GEOMETRY_TYPE_NAME")

    class Meta:
        managed = False
        db_table = "information_schema.st_geometry_columns"
        app_label = "gis"
        # Remove unique_together since we have a primary key
        # unique_together = (("TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME"),)

    @classmethod
    def table_name_col(cls):
        return "TABLE_NAME"

    @classmethod
    def geom_col_name(cls):
        return "COLUMN_NAME"

    def __str__(self):
        return (
            f"{self.TABLE_SCHEMA}.{self.TABLE_NAME}.{self.COLUMN_NAME} "
            f"({self.GEOMETRY_TYPE_NAME}, SRID: {self.SRS_ID})"
        )


class MySQLSpatialRefSys(models.Model, SpatialRefSysMixin):
    """Real model for MySQL 8.0 ST_SPATIAL_REFERENCE_SYSTEMS view."""

    SRS_NAME = models.CharField(max_length=80, primary_key=True, db_column="SRS_NAME")
    SRS_ID = models.IntegerField(unique=True, db_column="SRS_ID")
    ORGANIZATION = models.CharField(max_length=256, db_column="ORGANIZATION")
    ORGANIZATION_COORDSYS_ID = models.IntegerField(db_column="ORGANIZATION_COORDSYS_ID")
    DEFINITION = models.TextField(db_column="DEFINITION")
    DESCRIPTION = models.TextField(blank=True, null=True, db_column="DESCRIPTION")

    class Meta:
        managed = False
        db_table = "information_schema.st_spatial_reference_systems"
        app_label = "gis"

    @property
    def wkt(self):
        return self.DEFINITION

    @property
    def srid(self):
        return self.SRS_ID

    @property
    def auth_name(self):
        return self.ORGANIZATION

    @property
    def auth_srid(self):
        return self.ORGANIZATION_COORDSYS_ID

    @property
    def srtext(self):
        return self.DEFINITION

    @property
    def proj4text(self):
        """Convert WKT to Proj4 if needed."""
        # This is a simplification - real conversion would be more complex
        return "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

    def get_units(self, wkt=None):
        """Return units for this SRS."""
        from django.contrib.gis.measure import D

        return D["m"], "meter"

    def get_ellipsoid(self, wkt=None):
        """Return ellipsoid parameters."""
        return (6378137.0, 6356752.3142)  # WGS84 ellipsoid for most

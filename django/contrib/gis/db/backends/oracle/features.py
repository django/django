from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.db.backends.oracle.features import (
    DatabaseFeatures as OracleDatabaseFeatures,
)
from django.utils.functional import cached_property


class DatabaseFeatures(BaseSpatialFeatures, OracleDatabaseFeatures):
    supports_add_srs_entry = False
    supports_geometry_field_introspection = False
    supports_geometry_field_unique_index = False
    supports_perimeter_geodetic = True
    supports_dwithin_distance_expr = False
    supports_tolerance_parameter = True
    unsupported_geojson_options = {"bbox", "crs", "precision"}

    @cached_property
    def django_test_skips(self):
        skips = super().django_test_skips
        skips.update(
            {
                "Oracle doesn't support spatial operators in constraints.": {
                    "gis_tests.gis_migrations.test_operations.OperationTests."
                    "test_add_check_constraint",
                },
                "Oracle doesn't support nested geometry collections.": {
                    "gis_tests.geoapp.tests.SaveLoadTests."
                    "test_geometrycollectionfield_default_max_ignored_on_read",
                },
            }
        )
        if self.connection.oracle_version >= (23, 9):
            skips.update(
                {
                    "Oracle 23ai unpacks 1-element geometry collections.": {
                        "gis_tests.geogapp.tests.GeographyTest."
                        "test05_geography_layermapping",
                        "gis_tests.layermap.tests.LayerMapTest."
                        "test_layermap_unique_multigeometry_fk",
                        "gis_tests.layermap.tests.LayerMapTest."
                        "test_null_geom_with_unique",
                        "gis_tests.layermap.tests.LayerMapTest."
                        "test_test_fid_range_step",
                    },
                },
            )
        return skips

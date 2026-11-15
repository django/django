import copy
from unittest import mock

from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.db.models.fields import BaseSpatialField
from django.contrib.gis.db.models.sql import AreaField, DistanceField
from django.test import SimpleTestCase


class FieldsTests(SimpleTestCase):
    def test_area_field_deepcopy(self):
        field = AreaField(None)
        self.assertEqual(copy.deepcopy(field), field)

    def test_distance_field_deepcopy(self):
        field = DistanceField(None)
        self.assertEqual(copy.deepcopy(field), field)


class GeometryFieldTests(SimpleTestCase):
    def test_deconstruct_empty(self):
        field = GeometryField()
        *_, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {"srid": 4326})

    def test_deconstruct_values(self):
        field = GeometryField(
            srid=4067,
            dim=3,
            geography=True,
            extent=(
                50199.4814,
                6582464.0358,
                -50000.0,
                761274.6247,
                7799839.8902,
                50000.0,
            ),
            tolerance=0.01,
        )
        *_, kwargs = field.deconstruct()
        self.assertEqual(
            kwargs,
            {
                "srid": 4067,
                "dim": 3,
                "geography": True,
                "extent": (
                    50199.4814,
                    6582464.0358,
                    -50000.0,
                    761274.6247,
                    7799839.8902,
                    50000.0,
                ),
                "tolerance": 0.01,
            },
        )

    def test_deconstruct_max_geom_collections(self):
        # The default is omitted, a custom value is preserved.
        field = GeometryField()
        *_, kwargs = field.deconstruct()
        self.assertNotIn("max_geom_collections", kwargs)

        field = GeometryField(max_geom_collections=128)
        *_, kwargs = field.deconstruct()
        self.assertEqual(kwargs["max_geom_collections"], 128)

    def test_formfield_forwards_max_geom_collections(self):
        field = GeometryField(max_geom_collections=128)
        self.assertEqual(field.formfield().max_geom_collections, 128)

    def test_get_prep_value_without_max_geom_collections_uses_default(self):
        # A spatial field that is not RASTER nor defines max_geom_collections
        # still applies the default limit when preparing a lookup value.
        class AttrlessSpatialField(BaseSpatialField):
            geom_type = "GEOMETRY"

        field = AttrlessSpatialField()
        geom = "POINT(0 0)"
        for _ in range(6):
            geom = f"GEOMETRYCOLLECTION({geom})"
        msg = "WKT contains too many possible GeometryCollections."
        with (
            mock.patch("django.contrib.gis.db.models.fields.MAX_GEOM_COLLECTIONS", 5),
            self.assertRaisesMessage(ValueError, msg),
        ):
            field.get_prep_value(geom)

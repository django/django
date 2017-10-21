import json

from django.contrib.gis.db.models.fields import BaseSpatialField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.db.models.lookups import DistanceLookupBase, GISLookup
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from django.contrib.gis.shortcuts import numpy
from django.db import connection
from django.db.models import Q
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from ..data.rasters.textrasters import JSON_RASTER
from .models import RasterModel, RasterRelatedModel


@skipUnlessDBFeature('supports_raster')
class RasterFieldTest(TransactionTestCase):
    available_apps = ['gis_tests.rasterapp']

    def setUp(self):
        rast = GDALRaster({
            "srid": 4326,
            "origin": [0, 0],
            "scale": [-1, 1],
            "skew": [0, 0],
            "width": 5,
            "height": 5,
            "nr_of_bands": 2,
            "bands": [{"data": range(25)}, {"data": range(25, 50)}],
        })
        model_instance = RasterModel.objects.create(
            rast=rast,
            rastprojected=rast,
            geom="POINT (-95.37040 29.70486)",
        )
        RasterRelatedModel.objects.create(rastermodel=model_instance)

    def test_field_null_value(self):
        """
        Test creating a model where the RasterField has a null value.
        """
        r = RasterModel.objects.create(rast=None)
        r.refresh_from_db()
        self.assertIsNone(r.rast)

    def test_access_band_data_directly_from_queryset(self):
        RasterModel.objects.create(rast=JSON_RASTER)
        qs = RasterModel.objects.all()
        qs[0].rast.bands[0].data()

    def test_model_creation(self):
        """
        Test RasterField through a test model.
        """
        # Create model instance from JSON raster
        r = RasterModel.objects.create(rast=JSON_RASTER)
        r.refresh_from_db()
        # Test raster metadata properties
        self.assertEqual((5, 5), (r.rast.width, r.rast.height))
        self.assertEqual([0.0, -1.0, 0.0, 0.0, 0.0, 1.0], r.rast.geotransform)
        self.assertIsNone(r.rast.bands[0].nodata_value)
        # Compare srs
        self.assertEqual(r.rast.srs.srid, 4326)
        # Compare pixel values
        band = r.rast.bands[0].data()
        # If numpy, convert result to list
        if numpy:
            band = band.flatten().tolist()
        # Loop through rows in band data and assert single
        # value is as expected.
        self.assertEqual(
            [
                0.0, 1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0, 9.0,
                10.0, 11.0, 12.0, 13.0, 14.0,
                15.0, 16.0, 17.0, 18.0, 19.0,
                20.0, 21.0, 22.0, 23.0, 24.0
            ],
            band
        )

    def test_implicit_raster_transformation(self):
        """
        Test automatic transformation of rasters with srid different from the
        field srid.
        """
        # Parse json raster
        rast = json.loads(JSON_RASTER)
        # Update srid to another value
        rast['srid'] = 3086
        # Save model and get it from db
        r = RasterModel.objects.create(rast=rast)
        r.refresh_from_db()
        # Confirm raster has been transformed to the default srid
        self.assertEqual(r.rast.srs.srid, 4326)
        # Confirm geotransform is in lat/lon
        expected = [
            -87.9298551266551, 9.459646421449934e-06, 0.0, 23.94249275457565,
            0.0, -9.459646421449934e-06,
        ]
        for val, exp in zip(r.rast.geotransform, expected):
            self.assertAlmostEqual(exp, val)

    def test_verbose_name_arg(self):
        """
        RasterField should accept a positional verbose name argument.
        """
        self.assertEqual(
            RasterModel._meta.get_field('rast').verbose_name,
            'A Verbose Raster Name'
        )

    def test_all_gis_lookups_with_rasters(self):
        """
        Evaluate all possible lookups for all input combinations (i.e.
        raster-raster, raster-geom, geom-raster) and for projected and
        unprojected coordinate systems. This test just checks that the lookup
        can be called, but doesn't check if the result makes logical sense.
        """
        from django.contrib.gis.db.backends.postgis.operations import PostGISOperations

        # Create test raster and geom.
        rast = GDALRaster(json.loads(JSON_RASTER))
        stx_pnt = GEOSGeometry('POINT (-95.370401017314293 29.704867409475465)', 4326)
        stx_pnt.transform(3086)

        lookups = [
            (name, lookup)
            for name, lookup in BaseSpatialField.get_lookups().items()
            if issubclass(lookup, GISLookup)
        ]
        self.assertNotEqual(lookups, [], 'No lookups found')
        # Loop through all the GIS lookups.
        for name, lookup in lookups:
            # Construct lookup filter strings.
            combo_keys = [
                field + name for field in [
                    'rast__', 'rast__', 'rastprojected__0__', 'rast__',
                    'rastprojected__', 'geom__', 'rast__',
                ]
            ]
            if issubclass(lookup, DistanceLookupBase):
                # Set lookup values for distance lookups.
                combo_values = [
                    (rast, 50, 'spheroid'),
                    (rast, 0, 50, 'spheroid'),
                    (rast, 0, D(km=1)),
                    (stx_pnt, 0, 500),
                    (stx_pnt, D(km=1000)),
                    (rast, 500),
                    (json.loads(JSON_RASTER), 500),
                ]
            elif name == 'relate':
                # Set lookup values for the relate lookup.
                combo_values = [
                    (rast, 'T*T***FF*'),
                    (rast, 0, 'T*T***FF*'),
                    (rast, 0, 'T*T***FF*'),
                    (stx_pnt, 0, 'T*T***FF*'),
                    (stx_pnt, 'T*T***FF*'),
                    (rast, 'T*T***FF*'),
                    (json.loads(JSON_RASTER), 'T*T***FF*'),
                ]
            elif name == 'isvalid':
                # The isvalid lookup doesn't make sense for rasters.
                continue
            elif PostGISOperations.gis_operators[name].func:
                # Set lookup values for all function based operators.
                combo_values = [
                    rast, (rast, 0), (rast, 0), (stx_pnt, 0), stx_pnt,
                    rast, json.loads(JSON_RASTER)
                ]
            else:
                # Override band lookup for these, as it's not supported.
                combo_keys[2] = 'rastprojected__' + name
                # Set lookup values for all other operators.
                combo_values = [rast, None, rast, stx_pnt, stx_pnt, rast, json.loads(JSON_RASTER)]

            # Create query filter combinations.
            self.assertEqual(
                len(combo_keys),
                len(combo_values),
                'Number of lookup names and values should be the same',
            )
            combos = [x for x in zip(combo_keys, combo_values) if x[1]]
            self.assertEqual(
                [(n, x) for n, x in enumerate(combos) if x in combos[:n]],
                [],
                'There are repeated test lookups',
            )
            combos = [{k: v} for k, v in combos]

            for combo in combos:
                # Apply this query filter.
                qs = RasterModel.objects.filter(**combo)

                # Evaluate normal filter qs.
                self.assertIn(qs.count(), [0, 1])

            # Evaluate on conditional Q expressions.
            qs = RasterModel.objects.filter(Q(**combos[0]) & Q(**combos[1]))
            self.assertIn(qs.count(), [0, 1])

    def test_dwithin_gis_lookup_ouptut_with_rasters(self):
        """
        Check the logical functionality of the dwithin lookup for different
        input parameters.
        """
        # Create test raster and geom.
        rast = GDALRaster(json.loads(JSON_RASTER))
        stx_pnt = GEOSGeometry('POINT (-95.370401017314293 29.704867409475465)', 4326)
        stx_pnt.transform(3086)

        # Filter raster with different lookup raster formats.
        qs = RasterModel.objects.filter(rastprojected__dwithin=(rast, D(km=1)))
        self.assertEqual(qs.count(), 1)

        qs = RasterModel.objects.filter(rastprojected__dwithin=(json.loads(JSON_RASTER), D(km=1)))
        self.assertEqual(qs.count(), 1)

        qs = RasterModel.objects.filter(rastprojected__dwithin=(JSON_RASTER, D(km=1)))
        self.assertEqual(qs.count(), 1)

        # Filter in an unprojected coordinate system.
        qs = RasterModel.objects.filter(rast__dwithin=(rast, 40))
        self.assertEqual(qs.count(), 1)

        # Filter with band index transform.
        qs = RasterModel.objects.filter(rast__1__dwithin=(rast, 1, 40))
        self.assertEqual(qs.count(), 1)
        qs = RasterModel.objects.filter(rast__1__dwithin=(rast, 40))
        self.assertEqual(qs.count(), 1)
        qs = RasterModel.objects.filter(rast__dwithin=(rast, 1, 40))
        self.assertEqual(qs.count(), 1)

        # Filter raster by geom.
        qs = RasterModel.objects.filter(rast__dwithin=(stx_pnt, 500))
        self.assertEqual(qs.count(), 1)

        qs = RasterModel.objects.filter(rastprojected__dwithin=(stx_pnt, D(km=10000)))
        self.assertEqual(qs.count(), 1)

        qs = RasterModel.objects.filter(rast__dwithin=(stx_pnt, 5))
        self.assertEqual(qs.count(), 0)

        qs = RasterModel.objects.filter(rastprojected__dwithin=(stx_pnt, D(km=100)))
        self.assertEqual(qs.count(), 0)

        # Filter geom by raster.
        qs = RasterModel.objects.filter(geom__dwithin=(rast, 500))
        self.assertEqual(qs.count(), 1)

        # Filter through related model.
        qs = RasterRelatedModel.objects.filter(rastermodel__rast__dwithin=(rast, 40))
        self.assertEqual(qs.count(), 1)

        # Filter through related model with band index transform
        qs = RasterRelatedModel.objects.filter(rastermodel__rast__1__dwithin=(rast, 40))
        self.assertEqual(qs.count(), 1)

        # Filter through conditional statements.
        qs = RasterModel.objects.filter(Q(rast__dwithin=(rast, 40)) & Q(rastprojected__dwithin=(stx_pnt, D(km=10000))))
        self.assertEqual(qs.count(), 1)

        # Filter through different lookup.
        qs = RasterModel.objects.filter(rastprojected__bbcontains=rast)
        self.assertEqual(qs.count(), 1)

    def test_lookup_input_tuple_too_long(self):
        rast = GDALRaster(json.loads(JSON_RASTER))
        msg = 'Tuple too long for lookup bbcontains.'
        with self.assertRaisesMessage(ValueError, msg):
            RasterModel.objects.filter(rast__bbcontains=(rast, 1, 2))

    def test_lookup_input_band_not_allowed(self):
        rast = GDALRaster(json.loads(JSON_RASTER))
        qs = RasterModel.objects.filter(rast__bbcontains=(rast, 1))
        msg = 'Band indices are not allowed for this operator, it works on bbox only.'
        with self.assertRaisesMessage(ValueError, msg):
            qs.count()

    def test_isvalid_lookup_with_raster_error(self):
        qs = RasterModel.objects.filter(rast__isvalid=True)
        msg = 'IsValid function requires a GeometryField in position 1, got RasterField.'
        with self.assertRaisesMessage(TypeError, msg):
            qs.count()

    def test_result_of_gis_lookup_with_rasters(self):
        # Point is in the interior
        qs = RasterModel.objects.filter(rast__contains=GEOSGeometry('POINT (-0.5 0.5)', 4326))
        self.assertEqual(qs.count(), 1)
        # Point is in the exterior
        qs = RasterModel.objects.filter(rast__contains=GEOSGeometry('POINT (0.5 0.5)', 4326))
        self.assertEqual(qs.count(), 0)
        # A point on the boundary is not contained properly
        qs = RasterModel.objects.filter(rast__contains_properly=GEOSGeometry('POINT (0 0)', 4326))
        self.assertEqual(qs.count(), 0)
        # Raster is located left of the point
        qs = RasterModel.objects.filter(rast__left=GEOSGeometry('POINT (1 0)', 4326))
        self.assertEqual(qs.count(), 1)

    def test_lookup_with_raster_bbox(self):
        rast = GDALRaster(json.loads(JSON_RASTER))
        # Shift raster upwards
        rast.origin.y = 2
        # The raster in the model is not strictly below
        qs = RasterModel.objects.filter(rast__strictly_below=rast)
        self.assertEqual(qs.count(), 0)
        # Shift raster further upwards
        rast.origin.y = 6
        # The raster in the model is strictly below
        qs = RasterModel.objects.filter(rast__strictly_below=rast)
        self.assertEqual(qs.count(), 1)

    def test_lookup_with_polygonized_raster(self):
        rast = GDALRaster(json.loads(JSON_RASTER))
        # Move raster to overlap with the model point on the left side
        rast.origin.x = -95.37040 + 1
        rast.origin.y = 29.70486
        # Raster overlaps with point in model
        qs = RasterModel.objects.filter(geom__intersects=rast)
        self.assertEqual(qs.count(), 1)
        # Change left side of raster to be nodata values
        rast.bands[0].data(data=[0, 0, 0, 1, 1], shape=(5, 1))
        rast.bands[0].nodata_value = 0
        qs = RasterModel.objects.filter(geom__intersects=rast)
        # Raster does not overlap anymore after polygonization
        # where the nodata zone is not included.
        self.assertEqual(qs.count(), 0)

    def test_lookup_value_error(self):
        # Test with invalid dict lookup parameter
        obj = {}
        msg = "Couldn't create spatial object from lookup value '%s'." % obj
        with self.assertRaisesMessage(ValueError, msg):
            RasterModel.objects.filter(geom__intersects=obj)
        # Test with invalid string lookup parameter
        obj = '00000'
        msg = "Couldn't create spatial object from lookup value '%s'." % obj
        with self.assertRaisesMessage(ValueError, msg):
            RasterModel.objects.filter(geom__intersects=obj)

    def test_db_function_errors(self):
        """
        Errors are raised when using DB functions with raster content.
        """
        point = GEOSGeometry("SRID=3086;POINT (-697024.9213808845 683729.1705516104)")
        rast = GDALRaster(json.loads(JSON_RASTER))
        msg = "Distance function requires a geometric argument in position 2."
        with self.assertRaisesMessage(TypeError, msg):
            RasterModel.objects.annotate(distance_from_point=Distance("geom", rast))
        with self.assertRaisesMessage(TypeError, msg):
            RasterModel.objects.annotate(distance_from_point=Distance("rastprojected", rast))
        msg = "Distance function requires a GeometryField in position 1, got RasterField."
        with self.assertRaisesMessage(TypeError, msg):
            RasterModel.objects.annotate(distance_from_point=Distance("rastprojected", point)).count()

    def test_lhs_with_index_rhs_without_index(self):
        with CaptureQueriesContext(connection) as queries:
            RasterModel.objects.filter(rast__0__contains=json.loads(JSON_RASTER)).exists()
        # It's easier to check the indexes in the generated SQL than to write
        # tests that cover all index combinations.
        self.assertRegex(queries[-1]['sql'], r'WHERE ST_Contains\([^)]*, 1, [^)]*, 1\)')

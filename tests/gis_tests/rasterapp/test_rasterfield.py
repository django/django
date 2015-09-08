import json
from unittest import skipIf

from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.shortcuts import numpy
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from ..data.rasters.textrasters import JSON_RASTER
from ..models import models
from .models import RasterModel


@skipUnlessDBFeature('supports_raster')
class RasterFieldTest(TransactionTestCase):
    available_apps = ['gis_tests.rasterapp']

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
        self.assertEqual(
            r.rast.geotransform,
            [-87.9298551266551, 9.459646421449934e-06, 0.0,
             23.94249275457565, 0.0, -9.459646421449934e-06]
        )

    def test_verbose_name_arg(self):
        """
        RasterField should accept a positional verbose name argument.
        """
        self.assertEqual(
            RasterModel._meta.get_field('rast').verbose_name,
            'A Verbose Raster Name'
        )


@skipIf(HAS_GDAL, 'Test raster field exception on systems without GDAL.')
class RasterFieldWithoutGDALTest(TestCase):

    def test_raster_field_without_gdal_exception(self):
        msg = 'RasterField requires GDAL.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            models.OriginalRasterField()

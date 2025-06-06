import os
import sys
from unittest import skipIf

from django.db import connection
from django.test import SimpleTestCase


class GDALImportTest(SimpleTestCase):
    """
    Test that importing django.contrib.gis.gdal.libgdal works without crashing
    when GDAL is not installed.

    This test only runs when GIS is not enabled (i.e., GDAL is not available).
    When GIS is enabled, the existing GIS test suite verifies functionality.
    """

    def setUp(self):
        if "django.contrib.gis.gdal.libgdal" in sys.modules:
            del sys.modules["django.contrib.gis.gdal.libgdal"]

    @skipIf(
        connection.features.gis_enabled,
        "Test only relevant when GIS is not enabled (GDAL not installed)",
    )
    @skipIf(os.name == "nt", "Separate Windows test handles both lgdal and lwingdal")
    def test_import_without_gdal(self):
        try:
            from django.contrib.gis.gdal import libgdal

            self.assertTrue(hasattr(libgdal, "lgdal"))
        except ImportError:
            self.fail(
                "Importing libgdal should not fail when GDAL is not installed. "
                "The lazy loading should defer errors until actual usage."
            )

    @skipIf(
        connection.features.gis_enabled,
        "Test only relevant when GIS is not enabled (GDAL not installed)",
    )
    @skipIf(os.name != "nt", "lwingdal is Windows-specific")
    def test_import_without_gdal_windows(self):
        try:
            from django.contrib.gis.gdal import libgdal

            self.assertTrue(hasattr(libgdal, "lgdal"))
            self.assertTrue(hasattr(libgdal, "lwingdal"))
        except ImportError:
            self.fail(
                "Importing libgdal should not fail when GDAL is not installed. "
                "The lazy loading should defer errors until actual usage."
            )

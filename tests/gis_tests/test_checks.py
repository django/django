from unittest import mock

from django.contrib.gis.checks import check_gdal_39
from django.contrib.gis.gdal import GDAL_VERSION
from django.core.checks import Warning
from django.test import SimpleTestCase


class GISChecksTests(SimpleTestCase):
    def test_gdal_39_warning(self):
        msg = (
            "The installed version of GDAL does not allow blocking file and "
            "network access. Upgrade to GDAL 3.9 or higher to receive "
            "protection against malicious spatial references."
        )
        with mock.patch("django.contrib.gis.checks.GDAL_VERSION", (3, 8, 5)):
            self.assertEqual(
                check_gdal_39(None),
                [Warning(msg, hint=f"Your version: {GDAL_VERSION}", id="gis.W001")],
            )
        with mock.patch("django.contrib.gis.checks.GDAL_VERSION", (3, 9)):
            self.assertEqual(check_gdal_39(None), [])
        with mock.patch("django.contrib.gis.checks.GDAL_VERSION", (3, 9, 1)):
            self.assertEqual(check_gdal_39(None), [])

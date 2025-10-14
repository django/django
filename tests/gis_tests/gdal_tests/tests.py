import ctypes.util
import unittest
from importlib.util import find_spec, module_from_spec
from unittest import mock

from django.contrib.gis.gdal import GDAL_VERSION, gdal_full_version, gdal_version


class GDALTest(unittest.TestCase):
    def test_gdal_version(self):
        if GDAL_VERSION:
            self.assertEqual(
                gdal_version(), ("%s.%s.%s" % tuple(GDAL_VERSION)).encode()
            )
        else:
            self.assertIn(b".", gdal_version())

    def test_gdal_full_version(self):
        full_version = gdal_full_version()
        self.assertIn(gdal_version(), full_version)
        self.assertTrue(full_version.startswith(b"GDAL"))

    def test_gdal_not_available(self):
        with mock.patch.object(
            ctypes.util, "find_library", return_value=None
        ) as mock_find_library:
            # Does not raise ImproperlyConfigured
            module = reimport_module("django.contrib.gis.gdal.libgdal")
            # Verify module has the `lgdal` and that `reimport_module` worked
            self.assertTrue(hasattr(module, "lgdal"))
            # finally verify that lazy loading works and that `find_library` isn't
            # called on module import
            mock_find_library.assert_not_called()


def reimport_module(name):
    spec = find_spec(name)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

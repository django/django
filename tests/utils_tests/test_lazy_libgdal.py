import os
import sys
from unittest import skipIf

from django.test import SimpleTestCase
from django.utils.functional import SimpleLazyObject, empty


class GDALLazyLoadingTest(SimpleTestCase):
    """
    Testing for the lazy loading of the GDAL library - whether or not GDAL
    is installed - verifying that:

    - The GDAL library is not loaded upon importing `django.contrib.gis.gdal.libgdal`.
    - The library loading is attempted when the lazy object is accessed.

    The tests work regardless of whether GDAL is installed by tracking
    whether the load function is called, not whether it succeeds.
    """

    def setUp(self):
        libgdal_mod = "django.contrib.gis.gdal.libgdal"

        if libgdal_mod in sys.modules:
            del sys.modules[libgdal_mod]

    def test_lgdal_not_loaded_on_import(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIsInstance(libgdal.lgdal, SimpleLazyObject)
        self.assertTrue(hasattr(libgdal.lgdal, "_wrapped"))
        self.assertIs(libgdal.lgdal._wrapped, empty)

    @skipIf(os.name != "nt", "lwingdal is Windows-specific")
    def test_lwingdal_not_loaded_on_import(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIsInstance(libgdal.lwingdal, SimpleLazyObject)
        self.assertTrue(hasattr(libgdal.lwingdal, "_wrapped"))
        self.assertIs(libgdal.lwingdal._wrapped, empty)

    def test_lgdal_loaded_on_first_access(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIs(libgdal.lgdal._wrapped, empty)

        load_called = False
        lgdal_setupfunc = libgdal.lgdal.__dict__["_setupfunc"]

        def track_load():
            nonlocal load_called
            load_called = True
            return lgdal_setupfunc()

        # Modify __dict__ directly to avoid triggering lazy loading
        libgdal.lgdal.__dict__["_setupfunc"] = track_load

        try:
            libgdal.lgdal["GDALOpen"]
        except Exception:
            # Don't care if it fails, just that it tried
            pass
        finally:
            libgdal.lgdal.__dict__["_setupfunc"] = lgdal_setupfunc

        self.assertTrue(load_called)

    @skipIf(os.name != "nt", "lwingdal is Windows-specific")
    def test_lwingdal_loaded_on_first_access(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIs(libgdal.lwingdal._wrapped, empty)

        load_called = False
        lwingdal_setupfunc = libgdal.lwingdal.__dict__["_setupfunc"]

        def track_load():
            nonlocal load_called
            load_called = True
            return lwingdal_setupfunc()

        # Modify __dict__ directly to avoid triggering lazy loading
        libgdal.lwingdal.__dict__["_setupfunc"] = track_load

        try:
            # Access lwingdal to trigger loading
            libgdal.lwingdal["OSRNewSpatialReference"]
        except Exception:
            # Don't care if it fails, just that it tried
            pass
        finally:
            libgdal.lwingdal.__dict__["_setupfunc"] = lwingdal_setupfunc

        self.assertTrue(load_called)

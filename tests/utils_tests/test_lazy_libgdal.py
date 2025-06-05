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

    def test_lgdal_lazy_loading(self):
        from django.contrib.gis.gdal import libgdal

        # check that lgdal wasn't loaded on import
        self.assertIsInstance(libgdal.lgdal, SimpleLazyObject)
        self.assertTrue(hasattr(libgdal.lgdal, "_wrapped"))
        self.assertIs(libgdal.lgdal._wrapped, empty)

        # now check that lgdal gets loaded at first access
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
    def test_lwingdal_lazy_loading(self):
        from django.contrib.gis.gdal import libgdal

        # check that lwingdal wasn't loaded on import
        self.assertIsInstance(libgdal.lwingdal, SimpleLazyObject)
        self.assertTrue(hasattr(libgdal.lwingdal, "_wrapped"))
        self.assertIs(libgdal.lwingdal._wrapped, empty)

        # now check that lwingdal gets loaded at first access
        load_called = False
        lwingdal_setupfunc = libgdal.lwingdal.__dict__["_setupfunc"]

        def track_load():
            nonlocal load_called
            load_called = True
            return lwingdal_setupfunc()

        # Modify __dict__ directly to avoid triggering lazy loading
        libgdal.lwingdal.__dict__["_setupfunc"] = track_load

        try:
            libgdal.lwingdal["OSRNewSpatialReference"]
        except Exception:
            # Don't care if it fails, just that it tried
            pass
        finally:
            libgdal.lwingdal.__dict__["_setupfunc"] = lwingdal_setupfunc

        self.assertTrue(load_called)

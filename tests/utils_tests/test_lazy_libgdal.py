import os
import sys
from unittest import mock, skipIf

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.utils.functional import SimpleLazyObject, empty


class GDALLazyLoadingTest(SimpleTestCase):
    """
    Testing for the lazy loading of the GDAL library - whether or not GDAL
    is installed - verifying that:

    - The GDAL library is not loaded upon importing `django.contrib.gis.gdal.libgdal`.
    - The library is loaded only once upon the first access to an attribute
      of the lazy object.
    - Subsequent accesses do not reload the library.
    - The lazy objects use the `empty` sentinel from `django.utils.functional`
      to indicate whether the loading function has been called.
    - Appropriate exceptions are raised when the GDAL library cannot be found.

    The tests avoid dependency on the actual GDAL library by handling
    `AttributeError` from accessing non-existent attributes and by mocking
    where necessary.
    """

    def setUp(self):
        # Clean up modules before each test
        self.modules_to_clean = ["django.contrib.gis.gdal.libgdal"]
        for module in self.modules_to_clean:
            if module in sys.modules:
                del sys.modules[module]

    def tearDown(self):
        # Clean up after test
        for module in self.modules_to_clean:
            if module in sys.modules:
                del sys.modules[module]

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

        try:
            # Try to access a non-existent attribute
            # This should trigger the lazy loading
            with self.assertRaises(AttributeError):
                libgdal.lgdal.some_attribute

            self.assertIsNot(libgdal.lgdal._wrapped, empty)
        except ImproperlyConfigured:
            # GDAL is not installed, but our wrapper worked
            self.skipTest("GDAL is not installed")

    @skipIf(os.name != "nt", "lwingdal is Windows-specific")
    def test_lwingdal_loaded_on_first_access(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIs(libgdal.lwingdal._wrapped, empty)

        try:
            # Try to access a non-existent attribute
            # This should trigger the lazy loading
            with self.assertRaises(AttributeError):
                libgdal.lwingdal.some_attribute

            self.assertIsNot(libgdal.lwingdal._wrapped, empty)
        except ImproperlyConfigured:
            # GDAL is not installed, but our wrapper worked
            self.skipTest("GDAL is not installed")

    def test_lgdal_load_is_cached(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIs(libgdal.lgdal._wrapped, empty)

        try:
            # First access
            with self.assertRaises(AttributeError):
                libgdal.lgdal.some_attribute

            first_loaded_object = libgdal.lgdal._wrapped
            self.assertIsNot(first_loaded_object, empty)

            # Second access
            with self.assertRaises(AttributeError):
                libgdal.lgdal.another_attribute

            second_loaded_object = libgdal.lgdal._wrapped
            self.assertIsNot(second_loaded_object, empty)
            self.assertIs(second_loaded_object, first_loaded_object)
        except ImproperlyConfigured:
            # GDAL is not installed, but our wrapper worked
            self.skipTest("GDAL is not installed")

    @skipIf(os.name != "nt", "lwingdal is Windows-specific")
    def test_lwingdal_load_is_cached(self):
        from django.contrib.gis.gdal import libgdal

        self.assertIs(libgdal.lwingdal._wrapped, empty)

        try:
            # First access
            with self.assertRaises(AttributeError):
                libgdal.lwingdal.some_attribute

            first_loaded_object = libgdal.lwingdal._wrapped
            self.assertIsNot(first_loaded_object, empty)

            # Second access
            with self.assertRaises(AttributeError):
                libgdal.lwingdal.another_attribute

            second_loaded_object = libgdal.lwingdal._wrapped
            self.assertIsNot(second_loaded_object, empty)
            self.assertIs(second_loaded_object, first_loaded_object)
        except ImproperlyConfigured:
            # GDAL is not installed, but our wrapper worked
            self.skipTest("GDAL is not installed")

    @mock.patch("ctypes.util.find_library")
    def test_load_gdal_failure(self, mock_find_library):
        mock_find_library.return_value = None

        # Need to ensure the module is not already loaded
        if "django.contrib.gis.gdal.libgdal" in sys.modules:
            del sys.modules["django.contrib.gis.gdal.libgdal"]

        from django.contrib.gis.gdal import libgdal

        with self.assertRaisesMessage(
            ImproperlyConfigured, "Could not find the GDAL library"
        ):
            # Trigger the lazy loading
            libgdal.lgdal.some_attribute

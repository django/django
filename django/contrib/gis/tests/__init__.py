from unittest import TestSuite, makeSuite, TextTestRunner
import test_geos, test_gdal_ds, test_gdal_driver, test_gdal_srs, test_gdal_geom, test_spatialrefsys

def suite():
    s = TestSuite()
    s.addTest(test_geos.suite())
    s.addTest(test_gdal_ds.suite())
    s.addTest(test_gdal_driver.suite())
    s.addTest(test_gdal_srs.suite())
    s.addTest(test_gdal_geom.suite())
    s.addTest(test_spatialrefsys.suite())
    return s

def run(verbosity=1):
    TextTestRunner(verbosity=verbosity).run(suite())

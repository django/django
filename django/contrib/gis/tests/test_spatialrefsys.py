import unittest
from django.contrib.gis.tests.utils import mysql, no_mysql, oracle, postgis
if not mysql:
    from django.contrib.gis.models import SpatialRefSys

test_srs = ({'srid' : 4326,
             'auth_name' : ('EPSG', True),
             'auth_srid' : 4326,
             'srtext' : 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
             'proj4' : '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs ',
             'spheroid' : 'WGS 84', 'name' : 'WGS 84', 
             'geographic' : True, 'projected' : False,
             'ellipsoid' : (6378137.0, 6356752.3, 298.257223563), # From proj's "cs2cs -le" and Wikipedia (semi-minor only)
             'eprec' : (1, 1, 9),
             },
            {'srid' : 32140,
             'auth_name' : ('EPSG', False),
             'auth_srid' : 32140,
             'srtext' : 'PROJCS["NAD83 / Texas South Central",GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4269"]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",30.28333333333333],PARAMETER["standard_parallel_2",28.38333333333333],PARAMETER["latitude_of_origin",27.83333333333333],PARAMETER["central_meridian",-99],PARAMETER["false_easting",600000],PARAMETER["false_northing",4000000],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","32140"]]',
             'proj4' : '+proj=lcc +lat_1=30.28333333333333 +lat_2=28.38333333333333 +lat_0=27.83333333333333 +lon_0=-99 +x_0=600000 +y_0=4000000 +ellps=GRS80 +datum=NAD83 +units=m +no_defs ',
             'spheroid' : 'GRS 1980', 'name' : 'NAD83 / Texas South Central',
             'geographic' : False, 'projected' : True,
             'ellipsoid' : (6378137.0, 6356752.31414, 298.257222101), # From proj's "cs2cs -le" and Wikipedia (semi-minor only)
             'eprec' : (1, 5, 10),
             },
            )

class SpatialRefSysTest(unittest.TestCase):

    @no_mysql
    def test01_retrieve(self):
        "Testing retrieval of SpatialRefSys model objects."
        for sd in test_srs:
            srs = SpatialRefSys.objects.get(srid=sd['srid'])
            self.assertEqual(sd['srid'], srs.srid)

            # Some of the authority names are borked on Oracle, e.g., SRID=32140.
            #  also, Oracle Spatial seems to add extraneous info to fields, hence the
            #  the testing with the 'startswith' flag.
            auth_name, oracle_flag = sd['auth_name']
            if postgis or (oracle and oracle_flag):
                self.assertEqual(True, srs.auth_name.startswith(auth_name))
                
            self.assertEqual(sd['auth_srid'], srs.auth_srid)

            # No proj.4 and different srtext on oracle backends :(
            if postgis:
                self.assertEqual(sd['srtext'], srs.wkt)
                self.assertEqual(sd['proj4'], srs.proj4text)

    @no_mysql
    def test02_osr(self):
        "Testing getting OSR objects from SpatialRefSys model objects."
        for sd in test_srs:
            sr = SpatialRefSys.objects.get(srid=sd['srid'])
            self.assertEqual(True, sr.spheroid.startswith(sd['spheroid']))
            self.assertEqual(sd['geographic'], sr.geographic)
            self.assertEqual(sd['projected'], sr.projected)
            self.assertEqual(True, sr.name.startswith(sd['name']))

            # Testing the SpatialReference object directly.
            if postgis:
                srs = sr.srs
                self.assertEqual(sd['proj4'], srs.proj4)
                self.assertEqual(sd['srtext'], srs.wkt)

    @no_mysql
    def test03_ellipsoid(self):
        "Testing the ellipsoid property."
        for sd in test_srs:
            # Getting the ellipsoid and precision parameters.
            ellps1 = sd['ellipsoid']
            prec = sd['eprec']

            # Getting our spatial reference and its ellipsoid
            srs = SpatialRefSys.objects.get(srid=sd['srid'])
            ellps2 = srs.ellipsoid

            for i in range(3):
                param1 = ellps1[i]
                param2 = ellps2[i]
                self.assertAlmostEqual(ellps1[i], ellps2[i], prec[i])

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(SpatialRefSysTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())

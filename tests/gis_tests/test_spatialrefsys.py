import re

from django.test import TestCase, skipUnlessDBFeature

from .utils import SpatialRefSys, oracle, postgis, spatialite

test_srs = ({
    'srid': 4326,
    'auth_name': ('EPSG', True),
    'auth_srid': 4326,
    # Only the beginning, because there are differences depending on installed libs
    'srtext': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84"',
    # +ellps=WGS84 has been removed in the 4326 proj string in proj-4.8
    'proj4_re': r'\+proj=longlat (\+ellps=WGS84 )?(\+datum=WGS84 |\+towgs84=0,0,0,0,0,0,0 )\+no_defs ?',
    'spheroid': 'WGS 84', 'name': 'WGS 84',
    'geographic': True, 'projected': False, 'spatialite': True,
    # From proj's "cs2cs -le" and Wikipedia (semi-minor only)
    'ellipsoid': (6378137.0, 6356752.3, 298.257223563),
    'eprec': (1, 1, 9),
    'wkt': re.sub(r'[\s+]', '', """
        GEOGCS["WGS 84",
    DATUM["WGS_1984",
        SPHEROID["WGS 84",6378137,298.257223563,
            AUTHORITY["EPSG","7030"]],
        AUTHORITY["EPSG","6326"]],
    PRIMEM["Greenwich",0,
        AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.01745329251994328,
        AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]
    """)
}, {
    'srid': 32140,
    'auth_name': ('EPSG', False),
    'auth_srid': 32140,
    'srtext': (
        'PROJCS["NAD83 / Texas South Central",GEOGCS["NAD83",'
        'DATUM["North_American_Datum_1983",SPHEROID["GRS 1980"'
    ),
    'proj4_re': r'\+proj=lcc (\+lat_1=30.28333333333333? |\+lat_2=28.38333333333333? |\+lat_0=27.83333333333333? |'
                r'\+lon_0=-99 ){4}\+x_0=600000 \+y_0=4000000 (\+ellps=GRS80 )?'
                r'(\+datum=NAD83 |\+towgs84=0,0,0,0,0,0,0 )?\+units=m \+no_defs ?',
    'spheroid': 'GRS 1980', 'name': 'NAD83 / Texas South Central',
    'geographic': False, 'projected': True, 'spatialite': False,
    # From proj's "cs2cs -le" and Wikipedia (semi-minor only)
    'ellipsoid': (6378137.0, 6356752.31414, 298.257222101),
    'eprec': (1, 5, 10),
})


@skipUnlessDBFeature("has_spatialrefsys_table")
class SpatialRefSysTest(TestCase):

    def test_get_units(self):
        epsg_4326 = next(f for f in test_srs if f['srid'] == 4326)
        unit, unit_name = SpatialRefSys().get_units(epsg_4326['wkt'])
        self.assertEqual(unit_name, 'degree')
        self.assertAlmostEqual(unit, 0.01745329251994328)

    def test_retrieve(self):
        """
        Test retrieval of SpatialRefSys model objects.
        """
        for sd in test_srs:
            srs = SpatialRefSys.objects.get(srid=sd['srid'])
            self.assertEqual(sd['srid'], srs.srid)

            # Some of the authority names are borked on Oracle, e.g., SRID=32140.
            #  also, Oracle Spatial seems to add extraneous info to fields, hence the
            #  the testing with the 'startswith' flag.
            auth_name, oracle_flag = sd['auth_name']
            if postgis or (oracle and oracle_flag):
                self.assertTrue(srs.auth_name.startswith(auth_name))

            self.assertEqual(sd['auth_srid'], srs.auth_srid)

            # No proj.4 and different srtext on oracle backends :(
            if postgis:
                self.assertTrue(srs.wkt.startswith(sd['srtext']))
                self.assertRegex(srs.proj4text, sd['proj4_re'])

    def test_osr(self):
        """
        Test getting OSR objects from SpatialRefSys model objects.
        """
        for sd in test_srs:
            sr = SpatialRefSys.objects.get(srid=sd['srid'])
            self.assertTrue(sr.spheroid.startswith(sd['spheroid']))
            self.assertEqual(sd['geographic'], sr.geographic)
            self.assertEqual(sd['projected'], sr.projected)

            if not (spatialite and not sd['spatialite']):
                # Can't get 'NAD83 / Texas South Central' from PROJ.4 string
                # on SpatiaLite
                self.assertTrue(sr.name.startswith(sd['name']))

            # Testing the SpatialReference object directly.
            if postgis or spatialite:
                srs = sr.srs
                self.assertRegex(srs.proj4, sd['proj4_re'])
                self.assertTrue(srs.wkt.startswith(sd['srtext']))

    def test_ellipsoid(self):
        """
        Test the ellipsoid property.
        """
        for sd in test_srs:
            # Getting the ellipsoid and precision parameters.
            ellps1 = sd['ellipsoid']
            prec = sd['eprec']

            # Getting our spatial reference and its ellipsoid
            srs = SpatialRefSys.objects.get(srid=sd['srid'])
            ellps2 = srs.ellipsoid

            for i in range(3):
                self.assertAlmostEqual(ellps1[i], ellps2[i], prec[i])

    @skipUnlessDBFeature('supports_add_srs_entry')
    def test_add_entry(self):
        """
        Test adding a new entry in the SpatialRefSys model using the
        add_srs_entry utility.
        """
        from django.contrib.gis.utils import add_srs_entry

        add_srs_entry(3857)
        self.assertTrue(
            SpatialRefSys.objects.filter(srid=3857).exists()
        )
        srs = SpatialRefSys.objects.get(srid=3857)
        self.assertTrue(
            SpatialRefSys.get_spheroid(srs.wkt).startswith('SPHEROID[')
        )

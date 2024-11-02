from django.contrib.gis.gdal import (
    GDAL_VERSION,
    AxisOrder,
    CoordTransform,
    GDALException,
    SpatialReference,
    SRSException,
)
from django.contrib.gis.geos import GEOSGeometry
from django.test import SimpleTestCase


class TestSRS:
    def __init__(self, wkt, **kwargs):
        self.wkt = wkt
        for key, value in kwargs.items():
            setattr(self, key, value)


# Some Spatial Reference examples
srlist = (
    TestSRS(
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,'
        'AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",'
        '0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],'
        'AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
        epsg=4326,
        projected=False,
        geographic=True,
        local=False,
        lin_name="unknown",
        ang_name="degree",
        lin_units=1.0,
        ang_units=0.0174532925199,
        auth={
            None: ("EPSG", "4326"),  # Top-level authority.
            "GEOGCS": ("EPSG", "4326"),
            "spheroid": ("EPSG", "7030"),
        },
        attr=(
            ("DATUM", "WGS_1984"),
            (("SPHEROID", 1), "6378137"),
            ("primem|authority", "EPSG"),
        ),
    ),
    TestSRS(
        'PROJCS["NAD83 / Texas South Central",'
        'GEOGCS["NAD83",DATUM["North_American_Datum_1983",'
        'SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],'
        'AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","4269"]],PROJECTION["Lambert_Conformal_Conic_2SP"],'
        'PARAMETER["standard_parallel_1",30.2833333333333],'
        'PARAMETER["standard_parallel_2",28.3833333333333],'
        'PARAMETER["latitude_of_origin",27.8333333333333],'
        'PARAMETER["central_meridian",-99],PARAMETER["false_easting",600000],'
        'PARAMETER["false_northing",4000000],UNIT["metre",1,AUTHORITY["EPSG","9001"]],'
        'AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32140"]]',
        epsg=32140,
        projected=True,
        geographic=False,
        local=False,
        lin_name="metre",
        ang_name="degree",
        lin_units=1.0,
        ang_units=0.0174532925199,
        auth={
            None: ("EPSG", "32140"),  # Top-level authority.
            "PROJCS": ("EPSG", "32140"),
            "spheroid": ("EPSG", "7019"),
            "unit": ("EPSG", "9001"),
        },
        attr=(
            ("DATUM", "North_American_Datum_1983"),
            (("SPHEROID", 2), "298.257222101"),
            ("PROJECTION", "Lambert_Conformal_Conic_2SP"),
        ),
    ),
    TestSRS(
        'PROJCS["NAD83 / Texas South Central (ftUS)",'
        'GEOGCS["NAD83",DATUM["North_American_Datum_1983",'
        'SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],'
        'AUTHORITY["EPSG","6269"]],'
        'PRIMEM["Greenwich",0],'
        'UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],'
        'PARAMETER["false_easting",1968500],'
        'PARAMETER["false_northing",13123333.3333333],'
        'PARAMETER["central_meridian",-99],'
        'PARAMETER["standard_parallel_1",28.3833333333333],'
        'PARAMETER["standard_parallel_2",30.2833333333333],'
        'PARAMETER["latitude_of_origin",27.8333333333333],'
        'UNIT["US survey foot",0.304800609601219],AXIS["Easting",EAST],'
        'AXIS["Northing",NORTH]]',
        epsg=None,
        projected=True,
        geographic=False,
        local=False,
        lin_name="US survey foot",
        ang_name="Degree",
        lin_units=0.3048006096012192,
        ang_units=0.0174532925199,
        auth={
            None: (None, None),  # Top-level authority.
            "PROJCS": (None, None),
        },
        attr=(
            ("PROJCS|GeOgCs|spheroid", "GRS 1980"),
            (("projcs", 9), "UNIT"),
            (("projcs", 11), "AXIS"),
        ),
    ),
    # This is really ESRI format, not WKT -- but the import should work the same
    TestSRS(
        'LOCAL_CS["Non-Earth (Meter)",LOCAL_DATUM["Local Datum",32767],'
        'UNIT["Meter",1],AXIS["X",EAST],AXIS["Y",NORTH]]',
        esri=True,
        epsg=None,
        projected=False,
        geographic=False,
        local=True,
        lin_name="Meter",
        ang_name="degree",
        lin_units=1.0,
        ang_units=0.0174532925199,
        attr=(("LOCAL_DATUM", "Local Datum"),),
    ),
)

# Well-Known Names
well_known = (
    TestSRS(
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,'
        'AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.01745329251994328,'
        'AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
        wk="WGS84",
        name="WGS 84",
        attrs=(("GEOGCS|AUTHORITY", 1, "4326"), ("SPHEROID", "WGS 84")),
    ),
    TestSRS(
        'GEOGCS["WGS 72",DATUM["WGS_1972",SPHEROID["WGS 72",6378135,298.26,'
        'AUTHORITY["EPSG","7043"]],AUTHORITY["EPSG","6322"]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","4322"]]',
        wk="WGS72",
        name="WGS 72",
        attrs=(("GEOGCS|AUTHORITY", 1, "4322"), ("SPHEROID", "WGS 72")),
    ),
    TestSRS(
        'GEOGCS["NAD27",DATUM["North_American_Datum_1927",'
        'SPHEROID["Clarke 1866",6378206.4,294.9786982138982,'
        'AUTHORITY["EPSG","7008"]],AUTHORITY["EPSG","6267"]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","4267"]]',
        wk="NAD27",
        name="NAD27",
        attrs=(("GEOGCS|AUTHORITY", 1, "4267"), ("SPHEROID", "Clarke 1866")),
    ),
    TestSRS(
        'GEOGCS["NAD83",DATUM["North_American_Datum_1983",'
        'SPHEROID["GRS 1980",6378137,298.257222101,'
        'AUTHORITY["EPSG","7019"]],AUTHORITY["EPSG","6269"]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","4269"]]',
        wk="NAD83",
        name="NAD83",
        attrs=(("GEOGCS|AUTHORITY", 1, "4269"), ("SPHEROID", "GRS 1980")),
    ),
    TestSRS(
        'PROJCS["NZGD49 / Karamea Circuit",GEOGCS["NZGD49",'
        'DATUM["New_Zealand_Geodetic_Datum_1949",'
        'SPHEROID["International 1924",6378388,297,'
        'AUTHORITY["EPSG","7022"]],'
        "TOWGS84[59.47,-5.04,187.44,0.47,-0.1,1.024,-4.5993],"
        'AUTHORITY["EPSG","6272"]],PRIMEM["Greenwich",0,'
        'AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,'
        'AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4272"]],'
        'PROJECTION["Transverse_Mercator"],'
        'PARAMETER["latitude_of_origin",-41.28991152777778],'
        'PARAMETER["central_meridian",172.1090281944444],'
        'PARAMETER["scale_factor",1],PARAMETER["false_easting",300000],'
        'PARAMETER["false_northing",700000],'
        'UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","27216"]]',
        wk="EPSG:27216",
        name="NZGD49 / Karamea Circuit",
        attrs=(
            ("PROJECTION", "Transverse_Mercator"),
            ("SPHEROID", "International 1924"),
        ),
    ),
)

bad_srlist = (
    "Foobar",
    'OOJCS["NAD83 / Texas South Central",GEOGCS["NAD83",'
    'DATUM["North_American_Datum_1983",'
    'SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],'
    'AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],'
    'AUTHORITY["EPSG","4269"]],PROJECTION["Lambert_Conformal_Conic_2SP"],'
    'PARAMETER["standard_parallel_1",30.28333333333333],'
    'PARAMETER["standard_parallel_2",28.38333333333333],'
    'PARAMETER["latitude_of_origin",27.83333333333333],'
    'PARAMETER["central_meridian",-99],PARAMETER["false_easting",600000],'
    'PARAMETER["false_northing",4000000],UNIT["metre",1,'
    'AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","32140"]]',
)


class SpatialRefTest(SimpleTestCase):
    def test01_wkt(self):
        "Testing initialization on valid OGC WKT."
        for s in srlist:
            SpatialReference(s.wkt)

    def test02_bad_wkt(self):
        "Testing initialization on invalid WKT."
        for bad in bad_srlist:
            try:
                srs = SpatialReference(bad)
                srs.validate()
            except (SRSException, GDALException):
                pass
            else:
                self.fail('Should not have initialized on bad WKT "%s"!')

    def test03_get_wkt(self):
        "Testing getting the WKT."
        for s in srlist:
            srs = SpatialReference(s.wkt)
            # GDAL 3 strips UNIT part in the last occurrence.
            self.assertEqual(
                s.wkt.replace(',UNIT["Meter",1]', ""),
                srs.wkt.replace(',UNIT["Meter",1]', ""),
            )

    def test04_proj(self):
        """PROJ import and export."""
        proj_parts = [
            "+proj=longlat",
            "+ellps=WGS84",
            "+towgs84=0,0,0,0,0,0,0",
            "+datum=WGS84",
            "+no_defs",
        ]
        srs1 = SpatialReference(srlist[0].wkt)
        srs2 = SpatialReference("+proj=longlat +datum=WGS84 +no_defs")
        self.assertTrue(all(part in proj_parts for part in srs1.proj.split()))
        self.assertTrue(all(part in proj_parts for part in srs2.proj.split()))

    def test05_epsg(self):
        "Test EPSG import."
        for s in srlist:
            if s.epsg:
                srs1 = SpatialReference(s.wkt)
                srs2 = SpatialReference(s.epsg)
                srs3 = SpatialReference(str(s.epsg))
                srs4 = SpatialReference("EPSG:%d" % s.epsg)
                for srs in (srs1, srs2, srs3, srs4):
                    for attr, expected in s.attr:
                        self.assertEqual(expected, srs[attr])

    def test07_boolean_props(self):
        "Testing the boolean properties."
        for s in srlist:
            srs = SpatialReference(s.wkt)
            self.assertEqual(s.projected, srs.projected)
            self.assertEqual(s.geographic, srs.geographic)

    def test08_angular_linear(self):
        "Testing the linear and angular units routines."
        for s in srlist:
            srs = SpatialReference(s.wkt)
            self.assertEqual(s.ang_name, srs.angular_name)
            self.assertEqual(s.lin_name, srs.linear_name)
            self.assertAlmostEqual(s.ang_units, srs.angular_units, 9)
            self.assertAlmostEqual(s.lin_units, srs.linear_units, 9)

    def test09_authority(self):
        "Testing the authority name & code routines."
        for s in srlist:
            if hasattr(s, "auth"):
                srs = SpatialReference(s.wkt)
                for target, tup in s.auth.items():
                    self.assertEqual(tup[0], srs.auth_name(target))
                    self.assertEqual(tup[1], srs.auth_code(target))

    def test10_attributes(self):
        "Testing the attribute retrieval routines."
        for s in srlist:
            srs = SpatialReference(s.wkt)
            for tup in s.attr:
                att = tup[0]  # Attribute to test
                exp = tup[1]  # Expected result
                self.assertEqual(exp, srs[att])

    def test11_wellknown(self):
        "Testing Well Known Names of Spatial References."
        for s in well_known:
            srs = SpatialReference(s.wk)
            self.assertEqual(s.name, srs.name)
            for tup in s.attrs:
                if len(tup) == 2:
                    key = tup[0]
                    exp = tup[1]
                elif len(tup) == 3:
                    key = tup[:2]
                    exp = tup[2]
                self.assertEqual(srs[key], exp)

    def test12_coordtransform(self):
        "Testing initialization of a CoordTransform."
        target = SpatialReference("WGS84")
        CoordTransform(SpatialReference(srlist[0].wkt), target)

    def test13_attr_value(self):
        "Testing the attr_value() method."
        s1 = SpatialReference("WGS84")
        with self.assertRaises(TypeError):
            s1.__getitem__(0)
        with self.assertRaises(TypeError):
            s1.__getitem__(("GEOGCS", "foo"))
        self.assertEqual("WGS 84", s1["GEOGCS"])
        self.assertEqual("WGS_1984", s1["DATUM"])
        self.assertEqual("EPSG", s1["AUTHORITY"])
        self.assertEqual(4326, int(s1["AUTHORITY", 1]))
        self.assertIsNone(s1["FOOBAR"])

    def test_unicode(self):
        wkt = (
            'PROJCS["DHDN / Soldner 39 Langschoß",'
            'GEOGCS["DHDN",DATUM["Deutsches_Hauptdreiecksnetz",'
            'SPHEROID["Bessel 1841",6377397.155,299.1528128,AUTHORITY["EPSG","7004"]],'
            'AUTHORITY["EPSG","6314"]],'
            'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
            'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
            'AUTHORITY["EPSG","4314"]],PROJECTION["Cassini_Soldner"],'
            'PARAMETER["latitude_of_origin",50.66738711],'
            'PARAMETER["central_meridian",6.28935703],'
            'PARAMETER["false_easting",0],PARAMETER["false_northing",0],'
            'UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",NORTH],AXIS["Y",EAST],'
            'AUTHORITY["mj10777.de","187939"]]'
        )
        srs = SpatialReference(wkt)
        srs_list = [srs, srs.clone()]
        srs.import_wkt(wkt)

        for srs in srs_list:
            self.assertEqual(srs.name, "DHDN / Soldner 39 Langschoß")
            self.assertEqual(srs.wkt, wkt)
            self.assertIn("Langschoß", srs.pretty_wkt)
            if GDAL_VERSION < (3, 9):
                self.assertIn("Langschoß", srs.xml)

    def test_axis_order(self):
        wgs84_trad = SpatialReference(4326, axis_order=AxisOrder.TRADITIONAL)
        wgs84_auth = SpatialReference(4326, axis_order=AxisOrder.AUTHORITY)
        # Coordinate interpretation may depend on the srs axis predicate.
        pt = GEOSGeometry("POINT (992385.4472045 481455.4944650)", 2774)
        pt_trad = pt.transform(wgs84_trad, clone=True)
        self.assertAlmostEqual(pt_trad.x, -104.609, 3)
        self.assertAlmostEqual(pt_trad.y, 38.255, 3)
        pt_auth = pt.transform(wgs84_auth, clone=True)
        self.assertAlmostEqual(pt_auth.x, 38.255, 3)
        self.assertAlmostEqual(pt_auth.y, -104.609, 3)
        # clone() preserves the axis order.
        pt_auth = pt.transform(wgs84_auth.clone(), clone=True)
        self.assertAlmostEqual(pt_auth.x, 38.255, 3)
        self.assertAlmostEqual(pt_auth.y, -104.609, 3)

    def test_axis_order_invalid(self):
        msg = "SpatialReference.axis_order must be an AxisOrder instance."
        with self.assertRaisesMessage(ValueError, msg):
            SpatialReference(4326, axis_order="other")

    def test_esri(self):
        srs = SpatialReference("NAD83")
        pre_esri_wkt = srs.wkt
        srs.to_esri()
        self.assertNotEqual(srs.wkt, pre_esri_wkt)
        self.assertIn('DATUM["D_North_American_1983"', srs.wkt)
        srs.from_esri()
        self.assertIn('DATUM["North_American_Datum_1983"', srs.wkt)

    def test_srid(self):
        """The srid property returns top-level authority code."""
        for s in srlist:
            if hasattr(s, "epsg"):
                srs = SpatialReference(s.wkt)
                self.assertEqual(srs.srid, s.epsg)

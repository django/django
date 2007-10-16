"""
 This object provides the database adaptor for Oracle geometries.
"""
from cx_Oracle import CLOB

class OracleSpatialAdaptor(object):
    def __init__(self, geom):
        "Initializes only on the geometry object."
        self.wkt = geom.wkt

    def __str__(self):
        "WKT is used for the substitution value of the geometry."
        return self.wkt

    def oracle_type(self):
        """
        The parameter type is a CLOB because no string (VARCHAR2) greater
        than 4000 characters will be accepted through the Oracle database
        API and/or SQL*Plus.
        """
        return CLOB

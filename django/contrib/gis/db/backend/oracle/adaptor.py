from cx_Oracle import CLOB
from django.contrib.gis.db.backend.adaptor import WKTAdaptor

class OracleSpatialAdaptor(WKTAdaptor):
    input_size = CLOB

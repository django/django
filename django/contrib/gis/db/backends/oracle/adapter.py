from cx_Oracle import CLOB
from django.contrib.gis.db.backends.adapter import WKTAdapter

class OracleSpatialAdapter(WKTAdapter):
    input_size = CLOB

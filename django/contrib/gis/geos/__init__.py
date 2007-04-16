from GEOSGeometry import GEOSGeometry, GEOSException

def hex_to_wkt(hex):
    "Converts HEXEWKB into WKT."
    return GEOSGeometry(hex, 'hex').wkt

def wkt_to_hex(wkt):
    "Converts WKT into HEXEWKB."
    return GEOSGeometry(wkt, 'wkt').hex

def centroid(input, geom_type='hex'):
    "Returns the centroid of the geometry (given in HEXEWKB)."
    return GEOSGeometry(input, geom_type).centroid.wkt

def area(input, geom_type='hex'):
    "Returns the area of the geometry (given in HEXEWKB)."
    return GEOSGeometry(input, geom_type).area
    

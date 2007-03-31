from geos import geomFromWKT, geomToWKT, geomFromHEX, geomToHEX

def hex_to_wkt(hex):
    "Converts EWKBHEX into WKT."
    return geomToWKT(geomFromHEX(hex))

def wkt_to_hex(wkt):
    "Converts WKT into EWKBHEX."
    return geomToHEX(geomFromWKT(wkt))

def centroid(hex):
    "Returns the centroid of the geometry (given in EWKBHEX)."
    center = (geomFromHEX(hex)).getCentroid()
    return geomToWKT(center)

def area(hex):
    "Returns the area of the geometry (given in EWKBHEX)."
    return (geomFromHEX(hex)).area()
    

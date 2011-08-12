from django.contrib.gis.geos import GEOSGeometry, LinearRing, Polygon, Point
from django.contrib.gis.maps.google.gmap import GoogleMapException
from math import pi, sin, log, exp, atan

# Constants used for degree to radian conversion, and vice-versa.
DTOR = pi / 180.
RTOD = 180. / pi

class GoogleZoom(object):
    """
    GoogleZoom is a utility for performing operations related to the zoom
    levels on Google Maps.

    This class is inspired by the OpenStreetMap Mapnik tile generation routine
    `generate_tiles.py`, and the article "How Big Is the World" (Hack #16) in
    "Google Maps Hacks" by Rich Gibson and Schuyler Erle.

    `generate_tiles.py` may be found at:
      http://trac.openstreetmap.org/browser/applications/rendering/mapnik/generate_tiles.py

    "Google Maps Hacks" may be found at http://safari.oreilly.com/0596101619
    """
    
    def __init__(self, num_zoom=19, tilesize=256):
        "Initializes the Google Zoom object."
        # Google's tilesize is 256x256, square tiles are assumed.
        self._tilesize = tilesize
        
        # The number of zoom levels
        self._nzoom = num_zoom

        # Initializing arrays to hold the parameters for each one of the 
        # zoom levels.
        self._degpp = [] # Degrees per pixel
        self._radpp = [] # Radians per pixel
        self._npix  = [] # 1/2 the number of pixels for a tile at the given zoom level
        
        # Incrementing through the zoom levels and populating the parameter arrays.
        z = tilesize # The number of pixels per zoom level.
        for i in xrange(num_zoom):
            # Getting the degrees and radians per pixel, and the 1/2 the number of
            # for every zoom level.
            self._degpp.append(z / 360.) # degrees per pixel
            self._radpp.append(z / (2 * pi)) # radians per pixel
            self._npix.append(z / 2) # number of pixels to center of tile

            # Multiplying `z` by 2 for the next iteration.
            z *= 2

    def __len__(self):
        "Returns the number of zoom levels."
        return self._nzoom

    def get_lon_lat(self, lonlat):
        "Unpacks longitude, latitude from GEOS Points and 2-tuples."
        if isinstance(lonlat, Point):
            lon, lat = lonlat.coords
        else:
            lon, lat = lonlat
        return lon, lat

    def lonlat_to_pixel(self, lonlat, zoom):
        "Converts a longitude, latitude coordinate pair for the given zoom level."
        # Setting up, unpacking the longitude, latitude values and getting the
        # number of pixels for the given zoom level.
        lon, lat = self.get_lon_lat(lonlat)
        npix = self._npix[zoom]

        # Calculating the pixel x coordinate by multiplying the longitude value
        # with with the number of degrees/pixel at the given zoom level.
        px_x = round(npix + (lon * self._degpp[zoom]))

        # Creating the factor, and ensuring that 1 or -1 is not passed in as the 
        # base to the logarithm.  Here's why:
        #  if fac = -1, we'll get log(0) which is undefined; 
        #  if fac =  1, our logarithm base will be divided by 0, also undefined.
        fac = min(max(sin(DTOR * lat), -0.9999), 0.9999)

        # Calculating the pixel y coordinate.
        px_y = round(npix + (0.5 * log((1 + fac)/(1 - fac)) * (-1.0 * self._radpp[zoom])))

        # Returning the pixel x, y to the caller of the function.
        return (px_x, px_y)

    def pixel_to_lonlat(self, px, zoom):
        "Converts a pixel to a longitude, latitude pair at the given zoom level."
        if len(px) != 2:
            raise TypeError('Pixel should be a sequence of two elements.')

        # Getting the number of pixels for the given zoom level.
        npix = self._npix[zoom]

        # Calculating the longitude value, using the degrees per pixel.
        lon = (px[0] - npix) / self._degpp[zoom]

        # Calculating the latitude value.
        lat = RTOD * ( 2 * atan(exp((px[1] - npix)/ (-1.0 * self._radpp[zoom]))) - 0.5 * pi)

        # Returning the longitude, latitude coordinate pair.
        return (lon, lat)
    
    def tile(self, lonlat, zoom):
        """
        Returns a Polygon  corresponding to the region represented by a fictional
        Google Tile for the given longitude/latitude pair and zoom level. This
        tile is used to determine the size of a tile at the given point.
        """
        # The given lonlat is the center of the tile.
        delta = self._tilesize / 2

        # Getting the pixel coordinates corresponding to the
        # the longitude/latitude.
        px = self.lonlat_to_pixel(lonlat, zoom)

        # Getting the lower-left and upper-right lat/lon coordinates
        # for the bounding box of the tile.
        ll = self.pixel_to_lonlat((px[0]-delta, px[1]-delta), zoom)
        ur = self.pixel_to_lonlat((px[0]+delta, px[1]+delta), zoom)

        # Constructing the Polygon, representing the tile and returning.
        return Polygon(LinearRing(ll, (ll[0], ur[1]), ur, (ur[0], ll[1]), ll), srid=4326)
        
    def get_zoom(self, geom):
        "Returns the optimal Zoom level for the given geometry."
        # Checking the input type.
        if not isinstance(geom, GEOSGeometry) or geom.srid != 4326:
            raise TypeError('get_zoom() expects a GEOS Geometry with an SRID of 4326.')

        # Getting the envelope for the geometry, and its associated width, height
        # and centroid.
        env = geom.envelope
        env_w, env_h = self.get_width_height(env.extent)
        center = env.centroid

        for z in xrange(self._nzoom):
            # Getting the tile at the zoom level.
            tile_w, tile_h = self.get_width_height(self.tile(center, z).extent)

            # When we span more than one tile, this is an approximately good
            # zoom level.
            if (env_w > tile_w) or (env_h > tile_h):
                if z == 0: 
                    raise GoogleMapException('Geometry width and height should not exceed that of the Earth.')
                return z-1
        
        # Otherwise, we've zoomed in to the max.
        return self._nzoom-1

    def get_width_height(self, extent):
        """
        Returns the width and height for the given extent.
        """
        # Getting the lower-left, upper-left, and upper-right
        # coordinates from the extent.
        ll = Point(extent[:2])
        ul = Point(extent[0], extent[3])
        ur = Point(extent[2:])
        # Calculating the width and height.
        height = ll.distance(ul)
        width  = ul.distance(ur)
        return width, height

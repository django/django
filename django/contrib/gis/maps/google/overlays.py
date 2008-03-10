from django.contrib.gis.geos import LineString, LinearRing, Polygon
from django.utils.safestring import mark_safe

class GOverlayBase(object):
    def latlng_from_coords(self, coords):
        return '[%s]' % ','.join(['new GLatLng(%s,%s)' % (y, x) for x, y in coords])

    def __unicode__(self):
        "The string representation is the JavaScript API call."
        return mark_safe('%s(%s)' % (self.__class__.__name__, self.js_params))

class GPolygon(GOverlayBase):
    """
    A Python wrapper for the Google GPolygon object.  For more information
    please see the Google Maps API Reference:
     http://code.google.com/apis/maps/documentation/reference.html#GPolygon
    """
    def __init__(self, poly, 
                 stroke_color='#0000ff', stroke_weight=2, stroke_opacity=1,
                 fill_color='#0000ff', fill_opacity=0.4):
        """
        The GPolygon object initializes on a GEOS Polygon.  Please note that
        this will not depict Polygons with internal rings.

        Keyword Options:

          stroke_color:
            The color of the polygon outline. Defaults to '#0000ff' (blue).

          stroke_weight:
            The width of the polygon outline, in pixels.  Defaults to 2.

          stroke_opacity:
            The opacity of the polygon outline, between 0 and 1.  Defaults to 1.

          fill_color:
            The color of the polygon fill.  Defaults to '#0000ff' (blue).

          fill_opacity:
            The opacity of the polygon fill.  Defaults to 0.4.
        """

        # TODO: Take other types of geometries.
        if not isinstance(poly, Polygon): 
            raise TypeError('GPolygon may only initialize on GEOS Polygons.')

        # Getting the envelope of the input polygon (used for automatically
        # determining the zoom level).
        self.envelope = poly.envelope

        # Translating the coordinates into a JavaScript array of 
        # Google `GLatLng` objects.
        self.points = self.latlng_from_coords(poly.shell.coords)

        # Stroke settings.
        self.stroke_color, self.stroke_opacity, self.stroke_weight = stroke_color, stroke_opacity, stroke_weight
      
        # Fill settings.
        self.fill_color, self.fill_opacity = fill_color, fill_opacity
        
    @property
    def js_params(self):
        return '%s, "%s", %s, %s, "%s", %s' % (self.points, self.stroke_color, self.stroke_weight, self.stroke_opacity,
                                               self.fill_color, self.fill_opacity)

class GPolyline(GOverlayBase):
    """
    A Python wrapper for the Google GPolyline object.  For more information
    please see the Google Maps API Reference:
     http://code.google.com/apis/maps/documentation/reference.html#GPolyline
    """
    def __init__(self, geom, color='#0000ff', weight=2, opacity=1):
        """
        The GPolyline object may initialize on GEOS LineStirng, LinearRing,
        and Polygon objects (internal rings not supported).  

        Keyword Options:
          
          color:
            The color to use for the polyline.  Defaults to '#0000ff' (blue).
  
          weight:
            The width of the polyline, in pixels.  Defaults to 2.

          opacity:
            The opacity of the polyline, between 0 and 1.  Defaults to 1.
        """
        if isinstance(geom, (LineString, LinearRing)):
            self.latlngs = self.latlng_from_coords(geom.coords)
        elif isinstance(geom, Polygon):
            self.latlngs = self.latlng_from_coords(geom.shell.coords)
        else:
            raise TypeError('GPolyline may only initialize on GEOS LineString, LinearRing, and/or Polygon geometries.')

        # Getting the envelope for automatic zoom determination.
        self.envelope = geom.envelope
        self.color, self.weight, self.opacity = color, weight, opacity
        
    @property
    def js_params(self):
        return '%s, "%s", %s, %s' % (self.latlngs, self.color, self.weight, self.opacity)

from django.utils.safestring import mark_safe
from django.contrib.gis.geos import fromstr, Point, LineString, LinearRing, Polygon

class GEvent(object):
    """
    A Python wrapper for the Google GEvent object.

    Events can be attached to any object derived from GOverlayBase with the
    add_event() call.

    For more information please see the Google Maps API Reference:
     http://code.google.com/apis/maps/documentation/reference.html#GEvent

    Example:

      from django.shortcuts import render_to_response
      from django.contrib.gis.maps.google import GoogleMap, GEvent, GPolyline

      def sample_request(request):
          polyline = GPolyline('LINESTRING(101 26, 112 26, 102 31)')
          event = GEvent('click', 
            'function() { location.href = "http://www.google.com"}')
          polyline.add_event(event)
          return render_to_response('mytemplate.html', 
          {'google' : GoogleMap(polylines=[polyline])})
    """

    def __init__(self, event, action):
        """
        Initializes a GEvent object. 
        
        Parameters:

        event: 
          string for the event, such as 'click'. The event must be a valid
          event for the object in the Google Maps API. 
          There is no validation of the event type within Django.

        action:
          string containing a Javascript function, such as 
          'function() { location.href = "newurl";}'
          The string must be a valid Javascript function. Again there is no 
          validation fo the function within Django.
        """
        self.event = event
        self.action = action

    def __unicode__(self):
        "Returns the parameter part of a GEvent."
        return mark_safe('"%s", %s' %(self.event, self.action))

class GOverlayBase(object):
    def __init__(self):
        self.events = []

    def latlng_from_coords(self, coords):
        "Generates a JavaScript array of GLatLng objects for the given coordinates."
        return '[%s]' % ','.join(['new GLatLng(%s,%s)' % (y, x) for x, y in coords])

    def add_event(self, event):
        "Attaches a GEvent to the overlay object."
        self.events.append(event)

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
        The GPolygon object initializes on a GEOS Polygon or a parameter that
        may be instantiated into GEOS Polygon.  Please note that this will not
        depict a Polygon's internal rings.

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
        if isinstance(poly, basestring): poly = fromstr(poly)
        if isinstance(poly, (tuple, list)): poly = Polygon(poly)
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
       
        super(GPolygon, self).__init__()
 
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
        The GPolyline object may be initialized on GEOS LineStirng, LinearRing,
        and Polygon objects (internal rings not supported) or a parameter that
        may instantiated into one of the above geometries.

        Keyword Options:
          
          color:
            The color to use for the polyline.  Defaults to '#0000ff' (blue).
  
          weight:
            The width of the polyline, in pixels.  Defaults to 2.

          opacity:
            The opacity of the polyline, between 0 and 1.  Defaults to 1.
        """
        # If a GEOS geometry isn't passed in, try to contsruct one.
        if isinstance(geom, basestring): geom = fromstr(geom)
        if isinstance(geom, (tuple, list)): geom = Polygon(geom)
        # Generating the lat/lng coordinate pairs.
        if isinstance(geom, (LineString, LinearRing)):
            self.latlngs = self.latlng_from_coords(geom.coords)
        elif isinstance(geom, Polygon):
            self.latlngs = self.latlng_from_coords(geom.shell.coords)
        else:
            raise TypeError('GPolyline may only initialize on GEOS LineString, LinearRing, and/or Polygon geometries.')

        # Getting the envelope for automatic zoom determination.
        self.envelope = geom.envelope
        self.color, self.weight, self.opacity = color, weight, opacity
        super(GPolyline, self).__init__()
        
    @property
    def js_params(self):
        return '%s, "%s", %s, %s' % (self.latlngs, self.color, self.weight, self.opacity)

class GMarker(GOverlayBase):
    """
    A Python wrapper for the Google GMarker object.  For more information
    please see the Google Maps API Reference:
     http://code.google.com/apis/maps/documentation/reference.html#GMarker

    Example:

      from django.shortcuts import render_to_response
      from django.contrib.gis.maps.google.overlays import GMarker, GEvent
     
      def sample_request(request):
          marker = GMarker('POINT(101 26)')
          event = GEvent('click', 
                         'function() { location.href = "http://www.google.com"}')
          marker.add_event(event)
          return render_to_response('mytemplate.html', 
                 {'google' : GoogleMap(markers=[marker])})
    """
    def __init__(self, geom, title=None, draggable=False):
        """
        The GMarker object may initialize on GEOS Points or a parameter
        that may be instantiated into a GEOS point.  Keyword options map to
        GMarkerOptions -- so far only the title option is supported.

        Keyword Options:
         title: 
           Title option for GMarker, will be displayed as a tooltip.
         
         draggable:
           Draggable option for GMarker, disabled by default.
        """
        # If a GEOS geometry isn't passed in, try to construct one.
        if isinstance(geom, basestring): geom = fromstr(geom)
        if isinstance(geom, (tuple, list)): geom = Point(geom)
        if isinstance(geom, Point):
            self.latlng = self.latlng_from_coords(geom.coords)
        else:
            raise TypeError('GMarker may only initialize on GEOS Point geometry.')
        # Getting the envelope for automatic zoom determination.
        self.envelope = geom.envelope
        # TODO: Add support for more GMarkerOptions
        self.title = title
        self.draggable = draggable
        super(GMarker, self).__init__()

    def latlng_from_coords(self, coords):
        return 'new GLatLng(%s,%s)' %(coords[1], coords[0])
    
    def options(self):
        result = []
        if self.title: result.append('title: "%s"' % self.title)
        if self.draggable: result.append('draggable: true') 
        return '{%s}' % ','.join(result)

    @property
    def js_params(self):
        return '%s, %s' % (self.latlng, self.options())

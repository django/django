from django.conf import settings
from django.template.loader import render_to_string

# The default Google Maps URL (for the API javascript)
# TODO: Internationalize for Japan, UK, etc.
GOOGLE_MAPS_URL='http://maps.google.com/maps?file=api&amp;v=%s&amp;key='

class GoogleMapException(Exception): pass
        
class GoogleMap(object):
    "A class for generating Google Maps javascript."

    # String constants
    onunload = 'onunload="GUnload()"' # Cleans up after Google Maps
    vml_css  = 'v\:* {behavior:url(#default#VML);}' # CSS for IE VML
    xmlns    = 'xmlns:v="urn:schemas-microsoft-com:vml"' # XML Namespace (for IE VML).

    def __init__(self, key=None, api_url=None, version=None,
                 center_lat=0.0, center_lon=0.0, zoom=1, 
                 dom_id='map', load_func='gmap_load', 
                 kml_urls=[], template='gis/google/js/google-map.js'):

        # The Google Maps API Key defined in the settings will be used
        #  if not passed in as a parameter.  The use of an API key is
        #  _required_.
        if not key:
            try:
                self._key = settings.GOOGLE_MAPS_API_KEY
            except AttributeError:
                raise GoogleMapException, 'Google Maps API Key not found (try adding GOOGLE_MAPS_API_KEY to your settings).'
        else:
            self._key = key
        
        # Getting the Google Maps API version, defaults to using the latest ("2.x"),
        #  this is not necessarily the most stable.
        if not version:
            try:
                self._version = settings.GOOGLE_MAPS_API_VERSION
            except AttributeError:
                self._version = '2.x'
        else:
            self._version = version

        # Can specify the API URL in the `api_url` keyword.
        if not api_url:
            try:
                self._url = settings.GOOGLE_MAPS_URL % self._version
            except AttributeError:
                self._url = GOOGLE_MAPS_URL % self._version
        else:
            self._url = api_url

        # Setting the DOM id of the map, the center lat/lon, the load function,
        #  and the zoom.
        self.dom_id = dom_id
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.load_func = load_func
        self.template = template
        self.zoom = zoom

        # Setting the parameters for the javascript template.
        params = {'center_lat' : center_lat,
                  'center_lon' : center_lon,
                  'dom_id' : dom_id,
                  'kml_urls' : kml_urls,
                  'load_func' : load_func,
                  'zoom' : zoom,
                  }
        self.js = render_to_string(template, params)

    @property
    def body(self):
        "Returns HTML body tag for loading and unloading Google Maps javascript."
        return '<body %s %s>' % (self.onload, self.onunload)

    @property
    def onload(self):
        "Returns the `onload` HTML <body> attribute."
        return 'onload="%s()"' % self.load_func

    @property
    def api_script(self):
        "Returns the <script> tag for the Google Maps API javascript."
        return '<script src="%s%s" type="text/javascript"></script>' % (self._url, self._key)

    @property
    def scripts(self):
        "Returns all <script></script> tags required for Google Maps JavaScript."
        return '%s\n  <script type="text/javascript">\n//<![CDATA[\n%s//]]>\n  </script>' % (self.api_script, self.js)

    @property
    def style(self):
        "Returns additional CSS styling needed for Google Maps on IE."
        return '<style type="text/css">%s</style>' % self.vml_css

    @property
    def xhtml(self):
        "Returns XHTML information needed for IE VML overlays."
        return '<html xmlns="http://www.w3.org/1999/xhtml" %s>' % self.xmlns

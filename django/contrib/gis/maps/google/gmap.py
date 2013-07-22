from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.six.moves import xrange

from django.contrib.gis.maps.google.overlays import GPolygon, GPolyline, GMarker

class GoogleMapException(Exception):
    pass


# The default Google Maps URL (for the API javascript)
# TODO: Internationalize for Japan, UK, etc.
GOOGLE_MAPS_URL='http://maps.google.com/maps?file=api&v=%s&key='


class GoogleMap(object):
    "A class for generating Google Maps JavaScript."

    # String constants
    onunload = mark_safe('onunload="GUnload()"') # Cleans up after Google Maps
    vml_css  = mark_safe('v\:* {behavior:url(#default#VML);}') # CSS for IE VML
    xmlns    = mark_safe('xmlns:v="urn:schemas-microsoft-com:vml"') # XML Namespace (for IE VML).

    def __init__(self, key=None, api_url=None, version=None,
                 center=None, zoom=None, dom_id='map',
                 kml_urls=[], polylines=None, polygons=None, markers=None,
                 template='gis/google/google-map.js',
                 js_module='geodjango',
                 extra_context={}):

        # The Google Maps API Key defined in the settings will be used
        # if not passed in as a parameter.  The use of an API key is
        # _required_.
        if not key:
            try:
                self.key = settings.GOOGLE_MAPS_API_KEY
            except AttributeError:
                raise GoogleMapException('Google Maps API Key not found (try adding GOOGLE_MAPS_API_KEY to your settings).')
        else:
            self.key = key

        # Getting the Google Maps API version, defaults to using the latest ("2.x"),
        # this is not necessarily the most stable.
        if not version:
            self.version = getattr(settings, 'GOOGLE_MAPS_API_VERSION', '2.x')
        else:
            self.version = version

        # Can specify the API URL in the `api_url` keyword.
        if not api_url:
            self.api_url = getattr(settings, 'GOOGLE_MAPS_URL', GOOGLE_MAPS_URL) % self.version
        else:
            self.api_url = api_url

        # Setting the DOM id of the map, the load function, the JavaScript
        # template, and the KML URLs array.
        self.dom_id = dom_id
        self.extra_context = extra_context
        self.js_module = js_module
        self.template = template
        self.kml_urls = kml_urls

        # Does the user want any GMarker, GPolygon, and/or GPolyline overlays?
        overlay_info = [[GMarker, markers, 'markers'],
                        [GPolygon, polygons, 'polygons'],
                        [GPolyline, polylines, 'polylines']]

        for overlay_class, overlay_list, varname in overlay_info:
            setattr(self, varname, [])
            if overlay_list:
                for overlay in overlay_list:
                    if isinstance(overlay, overlay_class):
                        getattr(self, varname).append(overlay)
                    else:
                        getattr(self, varname).append(overlay_class(overlay))

        # If GMarker, GPolygons, and/or GPolylines are used the zoom will be
        # automatically calculated via the Google Maps API.  If both a zoom
        # level and a center coordinate are provided with polygons/polylines,
        # no automatic determination will occur.
        self.calc_zoom = False
        if self.polygons or self.polylines  or self.markers:
            if center is None or zoom is None:
                self.calc_zoom = True

        # Defaults for the zoom level and center coordinates if the zoom
        # is not automatically calculated.
        if zoom is None: zoom = 4
        self.zoom = zoom
        if center is None: center = (0, 0)
        self.center = center

    def render(self):
        """
        Generates the JavaScript necessary for displaying this Google Map.
        """
        params = {'calc_zoom' : self.calc_zoom,
                  'center' : self.center,
                  'dom_id' : self.dom_id,
                  'js_module' : self.js_module,
                  'kml_urls' : self.kml_urls,
                  'zoom' : self.zoom,
                  'polygons' : self.polygons,
                  'polylines' : self.polylines,
                  'icons': self.icons,
                  'markers' : self.markers,
                  }
        params.update(self.extra_context)
        return render_to_string(self.template, params)

    @property
    def body(self):
        "Returns HTML body tag for loading and unloading Google Maps javascript."
        return format_html('<body {0} {1}>', self.onload, self.onunload)

    @property
    def onload(self):
        "Returns the `onload` HTML <body> attribute."
        return format_html('onload="{0}.{1}_load()"', self.js_module, self.dom_id)

    @property
    def api_script(self):
        "Returns the <script> tag for the Google Maps API javascript."
        return format_html('<script src="{0}{1}" type="text/javascript"></script>',
                           self.api_url, self.key)

    @property
    def js(self):
        "Returns only the generated Google Maps JavaScript (no <script> tags)."
        return self.render()

    @property
    def scripts(self):
        "Returns all <script></script> tags required with Google Maps JavaScript."
        return format_html('{0}\n  <script type="text/javascript">\n//<![CDATA[\n{1}//]]>\n  </script>',
                           self.api_script, mark_safe(self.js))

    @property
    def style(self):
        "Returns additional CSS styling needed for Google Maps on IE."
        return format_html('<style type="text/css">{0}</style>', self.vml_css)

    @property
    def xhtml(self):
        "Returns XHTML information needed for IE VML overlays."
        return format_html('<html xmlns="http://www.w3.org/1999/xhtml" {0}>', self.xmlns)

    @property
    def icons(self):
        "Returns a sequence of GIcon objects in this map."
        return set([marker.icon for marker in self.markers if marker.icon])

class GoogleMapSet(GoogleMap):

    def __init__(self, *args, **kwargs):
        """
        A class for generating sets of Google Maps that will be shown on the
        same page together.

        Example:
         gmapset = GoogleMapSet( GoogleMap( ... ), GoogleMap( ... ) )
         gmapset = GoogleMapSet( [ gmap1, gmap2] )
        """
        # The `google-multi.js` template is used instead of `google-single.js`
        # by default.
        template = kwargs.pop('template', 'gis/google/google-multi.js')

        # This is the template used to generate the GMap load JavaScript for
        # each map in the set.
        self.map_template = kwargs.pop('map_template', 'gis/google/google-single.js')

        # Running GoogleMap.__init__(), and resetting the template
        # value with default obtained above.
        super(GoogleMapSet, self).__init__(**kwargs)
        self.template = template

        # If a tuple/list passed in as first element of args, then assume
        if isinstance(args[0], (tuple, list)):
            self.maps = args[0]
        else:
            self.maps = args

        # Generating DOM ids for each of the maps in the set.
        self.dom_ids = ['map%d' % i for i in xrange(len(self.maps))]

    def load_map_js(self):
        """
        Returns JavaScript containing all of the loading routines for each
        map in this set.
        """
        result = []
        for dom_id, gmap in zip(self.dom_ids, self.maps):
            # Backup copies the GoogleMap DOM id and template attributes.
            # They are overridden on each GoogleMap instance in the set so
            # that only the loading JavaScript (and not the header variables)
            # is used with the generated DOM ids.
            tmp = (gmap.template, gmap.dom_id)
            gmap.template = self.map_template
            gmap.dom_id = dom_id
            result.append(gmap.js)
            # Restoring the backup values.
            gmap.template, gmap.dom_id = tmp
        return mark_safe(''.join(result))

    def render(self):
        """
        Generates the JavaScript for the collection of Google Maps in
        this set.
        """
        params = {'js_module' : self.js_module,
                  'dom_ids' : self.dom_ids,
                  'load_map_js' : self.load_map_js(),
                  'icons' : self.icons,
                  }
        params.update(self.extra_context)
        return render_to_string(self.template, params)

    @property
    def onload(self):
        "Returns the `onload` HTML <body> attribute."
        # Overloaded to use the `load` function defined in the
        # `google-multi.js`, which calls the load routines for
        # each one of the individual maps in the set.
        return mark_safe('onload="%s.load()"' % self.js_module)

    @property
    def icons(self):
        "Returns a sequence of all icons in each map of the set."
        icons = set()
        for map in self.maps: icons |= map.icons
        return icons

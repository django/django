"""
  This module houses the GoogleMap object, used for generating
   the needed javascript to embed Google Maps in a Web page.

  Google(R) is a registered trademark of Google, Inc. of Mountain View, California.

  Example:

   * In the view:
      return render(request, 'template.html', {'google': GoogleMap(key="abcdefg")})

   * In the template:

     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
       "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
     {{ google.xhtml }}
     <head>
       <title>Google Maps via GeoDjango</title>
       {{ google.style }}
       {{ google.scripts }}
     </head>
     {{ google.body }}
     <div id="{{ google.dom_id }}" style="width:600px;height:400px;"></div>
     </body>
     </html>

     Note:  If you want to be more explicit in your templates, the following are
      equivalent:
      {{ google.body }} => "<body {{ google.onload }} {{ google.onunload }}>"
      {{ google.xhtml }} => "<html xmlns="http://www.w3.org/1999/xhtml" {{ google.xmlns }}>"
      {{ google.style }} => "<style>{{ google.vml_css }}</style>"

  Explanation:
   - The `xhtml` property provides the correct XML namespace needed for
     Google Maps to operate in IE using XHTML.  Google Maps on IE uses
     VML to draw polylines.  Returns, by default:
     <html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml">

   - The `style` property provides the correct style tag for the CSS
     properties required by Google Maps on IE:
     <style type="text/css">v\:* {behavior:url(#default#VML);}</style>

   - The `scripts` property provides the necessary <script> tags for
     including the Google Maps javascript, as well as including the
     generated javascript.

   - The `body` property provides the correct attributes for the
     body tag to load the generated javascript.  By default, returns:
     <body onload="gmap_load()" onunload="GUnload()">

   - The `dom_id` property returns the DOM id for the map.  Defaults to "map".

  The following attributes may be set or customized in your local settings:
   * GOOGLE_MAPS_API_KEY: String of your Google Maps API key.  These are tied
      to a domain.  May be obtained from http://www.google.com/apis/maps/
   * GOOGLE_MAPS_API_VERSION (optional): Defaults to using "2.x"
   * GOOGLE_MAPS_URL (optional): Must have a substitution ('%s') for the API
      version.
"""
from django.contrib.gis.maps.google.gmap import GoogleMap, GoogleMapSet
from django.contrib.gis.maps.google.overlays import (
    GEvent, GIcon, GMarker, GPolygon, GPolyline,
)
from django.contrib.gis.maps.google.zoom import GoogleZoom

__all__ = [
    'GoogleMap', 'GoogleMapSet', 'GEvent', 'GIcon', 'GMarker', 'GPolygon',
    'GPolyline', 'GoogleZoom',
]

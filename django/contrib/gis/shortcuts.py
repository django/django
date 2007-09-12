from django.http import HttpResponse
from django.template import loader

def render_to_kml(*args, **kwargs):
    "Renders the response using the MIME type for KML."
    return HttpResponse(loader.render_to_string(*args, **kwargs),
                        mimetype='application/vnd.google-earth.kml+xml kml')

def render_to_text(*args, **kwargs):
    "Renders the response using the MIME type for plain text."
    return HttpResponse(loader.render_to_string(*args, **kwargs),
                        mimetype='text/plain')

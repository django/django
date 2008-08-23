import cStringIO, zipfile
from django.http import HttpResponse
from django.template import loader

def compress_kml(kml):
    "Returns compressed KMZ from the given KML string."
    kmz = cStringIO.StringIO()
    zf = zipfile.ZipFile(kmz, 'a', zipfile.ZIP_DEFLATED, False)
    zf.writestr('doc.kml', kml)
    zf.close()
    kmz.seek(0)
    return kmz.read()

def render_to_kml(*args, **kwargs):
    "Renders the response as KML (using the correct MIME type)."
    return HttpResponse(loader.render_to_string(*args, **kwargs),
                        mimetype='application/vnd.google-earth.kml+xml kml')

def render_to_kmz(*args, **kwargs):
    """
    Compresses the KML content and returns as KMZ (using the correct 
    MIME type).
    """
    return HttpResponse(compress_kml(loader.render_to_string(*args, **kwargs)),
                        mimetype='application/vnd.google-earth.kmz')


def render_to_text(*args, **kwargs):
    "Renders the response using the MIME type for plain text."
    return HttpResponse(loader.render_to_string(*args, **kwargs),
                        mimetype='text/plain')

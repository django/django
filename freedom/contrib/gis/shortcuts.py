import zipfile
from io import BytesIO

from freedom.conf import settings
from freedom.http import HttpResponse
from freedom.template import loader


def compress_kml(kml):
    "Returns compressed KMZ from the given KML string."
    kmz = BytesIO()
    zf = zipfile.ZipFile(kmz, 'a', zipfile.ZIP_DEFLATED)
    zf.writestr('doc.kml', kml.encode(settings.DEFAULT_CHARSET))
    zf.close()
    kmz.seek(0)
    return kmz.read()


def render_to_kml(*args, **kwargs):
    "Renders the response as KML (using the correct MIME type)."
    return HttpResponse(loader.render_to_string(*args, **kwargs),
        content_type='application/vnd.google-earth.kml+xml')


def render_to_kmz(*args, **kwargs):
    """
    Compresses the KML content and returns as KMZ (using the correct
    MIME type).
    """
    return HttpResponse(compress_kml(loader.render_to_string(*args, **kwargs)),
        content_type='application/vnd.google-earth.kmz')


def render_to_text(*args, **kwargs):
    "Renders the response using the MIME type for plain text."
    return HttpResponse(loader.render_to_string(*args, **kwargs),
        content_type='text/plain')

import re

from django.utils.text import compress_sequence, compress_string
from django.utils.cache import patch_vary_headers

re_accepts_gzip = re.compile(r'\bgzip\b')

class GZipMiddleware(object):
    """
    This middleware compresses content if the browser allows gzip compression.
    It sets the Vary header accordingly, so that caches will base their storage
    on the Accept-Encoding header.
    """
    streaming_safe = True

    def process_response(self, request, response):         
        # Do not consume the content of HttpResponseStreaming responses just to
        # check content length
        streaming = getattr(response, "content_generator", False)

        # It's not worth compressing non-OK or really short responses.
        if response.status_code != 200 or (not streaming and len(response.content) < 200):
            return response

        patch_vary_headers(response, ('Accept-Encoding',))

        # Avoid gzipping if we've already got a content-encoding.
        if response.has_header('Content-Encoding'):
            return response

        # MSIE have issues with gzipped respones of various content types.
        if "msie" in request.META.get('HTTP_USER_AGENT', '').lower():
            ctype = response.get('Content-Type', '').lower()
            if not ctype.startswith("text/") or "javascript" in ctype:
                return response

        ae = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if not re_accepts_gzip.search(ae):
            return response

        if streaming:
            response.content = compress_sequence(response.content_generator)
            del response['Content-Length']
        else:
            response.content = compress_string(response.content)
            response['Content-Length'] = str(len(response.content))
        response['Content-Encoding'] = 'gzip'
        return response

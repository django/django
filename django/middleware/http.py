from django.utils.cache import handle_conditional_get
from django.utils.http import http_date, parse_http_date_safe


class ConditionalGetMiddleware(object):
    """
    Handles conditional GET operations. If the response has an ETag or
    Last-Modified header, and the request has If-None-Match or
    If-Modified-Since, the response is replaced by an HttpNotModified.

    Also sets the Date and Content-Length response-headers.
    """
    def process_response(self, request, response):
        response['Date'] = http_date()
        if not response.streaming and not response.has_header('Content-Length'):
            response['Content-Length'] = str(len(response.content))

        etag = None
        if response.has_header('ETag'):
            etag = response['ETag']

        last_modified = None
        if response.has_header('Last-Modified'):
            last_modified = response['Last-Modified']
            if last_modified:
                last_modified = parse_http_date_safe(last_modified)

        if etag or last_modified:
            return handle_conditional_get(
                request,
                etag=etag,
                last_modified=last_modified,
                response=response,
            )

        return response

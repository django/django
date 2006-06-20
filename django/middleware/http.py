import datetime

class ConditionalGetMiddleware(object):
    """
    Handles conditional GET operations. If the response has a ETag or
    Last-Modified header, and the request has If-None-Match or
    If-Modified-Since, the response is replaced by an HttpNotModified.

    Removes the content from any response to a HEAD request.

    Also sets the Date and Content-Length response-headers.
    """
    def process_response(self, request, response):
        now = datetime.datetime.utcnow()
        response['Date'] = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        if not response.has_header('Content-Length'):
            response['Content-Length'] = str(len(response.content))

        if response.has_header('ETag'):
            if_none_match = request.META.get('HTTP_IF_NONE_MATCH', None)
            if if_none_match == response['ETag']:
                response.status_code = 304
                response.content = ''
                response['Content-Length'] = '0'

        if response.has_header('Last-Modified'):
            last_mod = response['Last-Modified']
            if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE', None)
            if if_modified_since == response['Last-Modified']:
                response.status_code = 304
                response.content = ''
                response['Content-Length'] = '0'

        if request.method == 'HEAD':
            response.content = ''

        return response

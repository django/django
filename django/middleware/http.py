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

        # If-None-Match must be ignored if original result would be anything
        # other than a 2XX or 304 status. 304 status would result in no change.
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.26
        if 200 <= response.status_code < 300 and response.has_header('ETag'):
            if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
            if if_none_match == response['ETag']:
                # Setting the status is enough here. The response handling path
                # automatically removes content for this status code (in
                # http.conditional_content_removal()).
                response.status_code = 304

        # If-Modified-Since must be ignored if the original result was not a 200.
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.25
        if response.status_code == 200 and response.has_header('Last-Modified'):
            if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
            if if_modified_since is not None:
                if_modified_since = parse_http_date_safe(if_modified_since)
            if if_modified_since is not None:
                last_modified = parse_http_date_safe(response['Last-Modified'])
                if last_modified is not None and last_modified <= if_modified_since:
                    # Setting the status code is enough here (same reasons as
                    # above).
                    response.status_code = 304

        return response

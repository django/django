from django.utils.cache import cc_delim_re, get_conditional_response, set_response_etag
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import parse_http_date_safe


class ConditionalGetMiddleware(MiddlewareMixin):
    """
    Handle conditional GET operations. If the response has an ETag or
    Last-Modified header and the request has If-None-Match or
    If-Modified-Since, replace the response with HttpNotModified. Add an ETag
    header if needed.
    """

    def process_response(self, request, response):
        # It's too late to prevent an unsafe request with a 412 response, and
        # for a HEAD request, the response body is always empty so computing
        # an accurate ETag isn't possible.
        if request.method != "GET":
            return response

        if self.needs_etag(response) and not response.has_header("ETag"):
            set_response_etag(response)

        etag = response.get("ETag")
        last_modified = response.get("Last-Modified")
        last_modified = last_modified and parse_http_date_safe(last_modified)

        if etag or last_modified:
            return get_conditional_response(
                request,
                etag=etag,
                last_modified=last_modified,
                response=response,
            )

        return response

    def needs_etag(self, response):
        """Return True if an ETag header should be added to response."""
        cache_control_headers = cc_delim_re.split(response.get("Cache-Control", ""))
        return all(header.lower() != "no-store" for header in cache_control_headers)

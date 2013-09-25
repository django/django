"""
Functions that modify an HTTP request or response in some way.
"""

# This group of functions are run as part of the response handling, after
# everything else, including all response middleware. Think of them as
# "compulsory response middleware". Be careful about what goes here, because
# it's a little fiddly to override this behavior, so they should be truly
# universally applicable.


def fix_location_header(request, response):
    """
    Ensures that we always use an absolute URI in any location header in the
    response. This is required by RFC 2616, section 14.30.

    Code constructing response objects is free to insert relative paths, as
    this function converts them to absolute paths.
    """
    if 'Location' in response and request.get_host():
        response['Location'] = request.build_absolute_uri(response['Location'])
    return response


def conditional_content_removal(request, response):
    """
    Removes the content of responses for HEAD requests, 1xx, 204 and 304
    responses. Ensures compliance with RFC 2616, section 4.3.
    """
    if 100 <= response.status_code < 200 or response.status_code in (204, 304):
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b''
        response['Content-Length'] = '0'
    if request.method == 'HEAD':
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b''
    return response


def fix_IE_for_attach(request, response):
    """
    This function will prevent Django from serving a Content-Disposition header
    while expecting the browser to cache it (only when the browser is IE). This
    leads to IE not allowing the client to download.
    """
    useragent = request.META.get('HTTP_USER_AGENT', '').upper()
    if 'MSIE' not in useragent and 'CHROMEFRAME' not in useragent:
        return response

    offending_headers = ('no-cache', 'no-store')
    if response.has_header('Content-Disposition'):
        try:
            del response['Pragma']
        except KeyError:
            pass
        if response.has_header('Cache-Control'):
            cache_control_values = [value.strip() for value in
                    response['Cache-Control'].split(',')
                    if value.strip().lower() not in offending_headers]

            if not len(cache_control_values):
                del response['Cache-Control']
            else:
                response['Cache-Control'] = ', '.join(cache_control_values)

    return response


def fix_IE_for_vary(request, response):
    """
    This function will fix the bug reported at
    http://support.microsoft.com/kb/824847/en-us?spid=8722&sid=global
    by clearing the Vary header whenever the mime-type is not safe
    enough for Internet Explorer to handle.  Poor thing.
    """
    useragent = request.META.get('HTTP_USER_AGENT', '').upper()
    if 'MSIE' not in useragent and 'CHROMEFRAME' not in useragent:
        return response

    # These mime-types that are decreed "Vary-safe" for IE:
    safe_mime_types = ('text/html', 'text/plain', 'text/sgml')

    # The first part of the Content-Type field will be the MIME type,
    # everything after ';', such as character-set, can be ignored.
    mime_type = response.get('Content-Type', '').partition(';')[0]
    if mime_type not in safe_mime_types:
        try:
            del response['Vary']
        except KeyError:
            pass

    return response

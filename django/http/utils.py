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
    if 'Location' in response:
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

"""
Clickjacking Protection Middleware.

This module provides a middleware that implements protection against a
malicious site loading resources from your site in a hidden frame.
"""

from django.conf import settings


class XFrameOptionsMiddleware(object):
    """
    Middleware that sets the X-Frame-Options HTTP header in HTTP responses.

    Does not set the header if it's already set or if the response contains
    a xframe_options_exempt value set to True.

    By default, sets the X-Frame-Options header to 'SAMEORIGIN', meaning the
    response can only be loaded on a frame within the same site. To prevent the
    response from being loaded in a frame in any site, set X_FRAME_OPTIONS in
    your project's Django settings to 'DENY'.

    Note: older browsers will quietly ignore this header, thus other
    clickjacking protection techniques should be used if protection in those
    browsers is required.

    https://en.wikipedia.org/wiki/Clickjacking#Server_and_client
    """
    def process_response(self, request, response):
        # Don't set it if it's already in the response
        if response.get('X-Frame-Options') is not None:
            return response

        # Don't set it if they used @xframe_options_exempt
        if getattr(response, 'xframe_options_exempt', False):
            return response

        response['X-Frame-Options'] = self.get_xframe_options_value(request,
                                                                    response)
        return response

    def get_xframe_options_value(self, request, response):
        """
        Gets the value to set for the X_FRAME_OPTIONS header.

        By default this uses the value from the X_FRAME_OPTIONS Django
        settings. If not found in settings, defaults to 'SAMEORIGIN'.

        This method can be overridden if needed, allowing it to vary based on
        the request or response.
        """
        return getattr(settings, 'X_FRAME_OPTIONS', 'SAMEORIGIN').upper()

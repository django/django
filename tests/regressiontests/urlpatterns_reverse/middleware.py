from django.core.urlresolvers import set_urlconf

import urlconf_inner

class ChangeURLconfMiddleware(object):
    def process_request(self, request):
        request.urlconf = urlconf_inner.__name__

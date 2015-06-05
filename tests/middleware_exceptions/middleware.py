from __future__ import unicode_literals

from django.http import HttpResponse


class ProcessExceptionMiddleware(object):
    def process_exception(self, request, exception):
        return HttpResponse('Exception caught')

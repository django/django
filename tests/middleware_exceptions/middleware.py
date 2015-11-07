from __future__ import unicode_literals

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class ProcessExceptionMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        return HttpResponse('Exception caught')

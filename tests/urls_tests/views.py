from __future__ import unicode_literals

from django.http import HttpResponse


def empty_view(request):
    """
    Return an empty response.
    """
    return HttpResponse('')


class ViewClass(object):
    def __call__(self, request):
        return HttpResponse('')

class_based_view = ViewClass()

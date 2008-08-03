from django.core import context_processors
from django.shortcuts import render_to_response
from django.template.context import RequestContext


def request_processor(request):
    return render_to_response('context_processors/request_attrs.html',
        RequestContext(request, {}, processors=[context_processors.request]))

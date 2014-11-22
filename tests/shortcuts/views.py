from django.shortcuts import render_to_response
from django.template import RequestContext


def context_processor(request):
    return {'output': 'context processor output'}


def request_context_misuse(request):
    context_instance = RequestContext(request, {}, processors=[context_processor])
    # Incorrect -- context_instance should be passed as a keyword argument.
    return render_to_response('shortcuts/output.html', context_instance)

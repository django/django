from __future__ import unicode_literals

from django.http import HttpResponse
from django.template import RequestContext, Template
from django.template.context_processors import csrf
from django.views.decorators.csrf import ensure_csrf_cookie


def post_form_view(request):
    """Return a POST form (without a token)."""
    return HttpResponse(content="""
<html><body><h1>\u00a1Unicode!<form method="post"><input type="text" /></form></body></html>
""", mimetype='text/html')


@ensure_csrf_cookie
def ensure_csrf_cookie_view(request):
    # Doesn't insert a token or anything.
    return HttpResponse()


def token_view(request):
    context = RequestContext(request, processors=[csrf])
    template = Template('{% csrf_token %}')
    return HttpResponse(template.render(context))


def non_token_view_using_request_processor(request):
    """Use the csrf view processor instead of the token."""
    context = RequestContext(request, processors=[csrf])
    template = Template('')
    return HttpResponse(template.render(context))

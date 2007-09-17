from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response

def index_page(request):
    """ Dummy index page """
    return HttpResponse('<html><body>Dummy page</body></html>')


def jsi18n_test(request):
    """ View for testing javascript message files """
    return render_to_response('js_i18n.html', {})

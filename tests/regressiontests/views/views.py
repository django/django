from django.http import HttpResponse
from django.template import RequestContext

def index_page(request):
    """Dummy index page"""
    return HttpResponse('<html><body>Dummy page</body></html>')


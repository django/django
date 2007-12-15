from django.http import HttpResponse

def index_page(request):
    """Dummy index page"""
    return HttpResponse('<html><body>Dummy page</body></html>')

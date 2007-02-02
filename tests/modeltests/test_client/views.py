from django.template import Context, Template
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

def get_view(request):
    "A simple view that expects a GET request, and returns a rendered template"
    t = Template('This is a test. {{ var }} is the value.', name='GET Template')
    c = Context({'var': 42})
    
    return HttpResponse(t.render(c))

def post_view(request):
    """A view that expects a POST, and returns a different template depending
    on whether any POST data is available
    """
    if request.POST:
        t = Template('Data received: {{ data }} is the value.', name='POST Template')
        c = Context({'data': request.POST['value']})
    else:
        t = Template('Viewing POST page.', name='Empty POST Template')
        c = Context()
        
    return HttpResponse(t.render(c))
    
def redirect_view(request):
    "A view that redirects all requests to the GET view"
    return HttpResponseRedirect('/test_client/get_view/')
    
def login_protected_view(request):
    "A simple view that is login protected."
    t = Template('This is a login protected test. Username is {{ user.username }}.', name='Login Template')
    c = Context({'user': request.user})
    
    return HttpResponse(t.render(c))
login_protected_view = login_required(login_protected_view)